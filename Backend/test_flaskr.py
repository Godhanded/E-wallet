import os
import unittest
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from auth.auth import encode_jwt
from flaskr import create_app
from flask_bcrypt import Bcrypt
from models import *


class WalletTestCase(unittest.TestCase):
    """This class represents the Wallet test case"""
    

    def setUp(self):
        """Define test variables and initialize app."""
        self.app = create_app()
        self.client = self.app.test_client
        self.database_name = "wallet_test"
        self.database_path = f'postgresql://postgres:postgres@localhost:5432/{self.database_name}'
        setup_db(self.app, self.database_path)
        bcrypt= Bcrypt(self.app);SALT = os.getenv("SALT")

        # binds the app to the current context
        with self.app.app_context():
            self.db = SQLAlchemy()
            self.db.init_app(self.app)
            # create all tables
            self.db.create_all()
        
        if Users.query.filter_by(email="test@email.com").first() is None:
            Users("testuser","testuser","test@email.com","test@email.com",bcrypt.generate_password_hash("test"+SALT).decode("utf-8"),datetime.utcnow().date().isoformat()).insert()
        
        if Users.query.filter_by(email="test2@email.com").first() is None:
            Users("testuser2","testuser2","test2@email.com","test2@email.com",bcrypt.generate_password_hash("test2"+SALT).decode("utf-8"),datetime.utcnow().date().isoformat()).insert()
        self.testjwt=encode_jwt("test@email.com",["get:users","post:users"])
        self.testjwt2=encode_jwt("test2@email.com",["get:users","post:users"])


    def tearDown(self):
        """Executed after reach test"""
        pass
    

    def test_encode_jwt(self):
        ''' it test jwt is encoded and exists'''
        self.assertTrue(self.testjwt and self.testjwt2)
        self.assertTrue(isinstance(self.testjwt,bytes)and isinstance(self.testjwt2,bytes))


    def test_hello(self):
        res = self.client().get("/")
        self.assertEqual(res.data.decode('UTF-8'), "hello world")

    def test_register_user(self):
        '''Test valid registration'''
        '''it should error if form is empty'''
        res= self.client().post("/users/register")
        data= json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["message"],"Bad Request")
        self.assertEqual(res.status_code,400)

        '''it should fail if user exists'''
        res= self.client().post("/users/register",json={"first_name":"test","last_name":"test",
        "email":"test2@email.com","username":"test2@email.com","password":"test2"})
        data=json.loads(res.data)
        self.assertTrue(res.status_code==403)
        self.assertTrue(data["message"]=="Sorry user already exists")

        '''it should register valid user'''
        res= self.client().post("/users/register",json={"first_name":"test","last_name":"test",
        "email":"test5@email.com","username":"test5@email.com","password":"test5"})
        
        data= json.loads(res.data)
        Users.query.filter_by(email="test5@email.com").one_or_none().delete()
        self.assertTrue(res.status_code==200)
        self.assertEqual(data["email"],"test5@email.com")

    def test_login_user(self):
        '''Test valid login'''
        '''it should fail if does not exist'''
        res=self.client().post("/users/login",json={"uname_or_mail":"test","password":"test"})
        data=json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertTrue(res.status_code==404)
        self.assertEqual(data["message"],"user does not exist")

        '''it should fail if password is wrong'''
        res= self.client().post("/users/login",json={"uname_or_mail":"test@email.com","password":"testfail"})
        data= json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertTrue(res.status_code,403)
        self.assertEqual(data["message"],"unauthorised")

        '''it should login valid user'''
        res= self.client().post("/users/login",json={"uname_or_mail":"test@email.com","password":"test"})
        data= json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertTrue(isinstance(data["jwt"],str))
        self.assertTrue(res.status_code==200)

    def test_get_user_balance(self):
        '''it should return a valid users balance'''
        '''it should fail if user has invalid loggedin token'''
        res=self.client().get("/users/balance",headers={"Authorization": f"Bearer {self.testjwt.decode('ASCII')}invalidstring"})
        data=json.loads(res.data)
        self.assertTrue(res.status_code==401)
        self.assertTrue(data["message"]=="Invalid token")
        
        '''it should fail if user in token deosnt exist'''
        mock_jwt=encode_jwt("notexists@email.com",["get:users","post:users"])
        res=self.client().get("/users/balance",headers={"Authorization": f"Bearer {mock_jwt.decode('ASCII')}"})
        data=json.loads(res.data)
        self.assertTrue(res.status_code==404)
        self.assertTrue(data["message"]=="user does not exist")
        
        '''it should return balance of valid user'''

        [wallet.delete() for wallet in UserWallet.query.filter_by(user="test@email.com" or "test2@email.com").all()]
        UserWallet(50,"test@email.com").insert()

        res= self.client().get("/users/balance",headers={"Authorization": f"Bearer {self.testjwt.decode('ASCII')}"})

        [wallet.delete() for wallet in UserWallet.query.filter_by(user="test@email.com" or "test2@email.com").all()]
        data=json.loads(res.data)
        self.assertTrue(res.status_code==200)
        self.assertTrue(data["balance"]==50)        

    def test_get_transactions(self):
        '''it should return user transactions paginated'''
        '''it should fail if user has invalid loggedin token'''
        res=self.client().get("/users/transactions",headers={"Authorization": f"Bearer {self.testjwt.decode('ASCII')}invalidstring"})
        data=json.loads(res.data)
        self.assertTrue(res.status_code==401)
        self.assertTrue(data["message"]=="Invalid token")
        
        '''it should fail if user in token deosnt exist'''
        mock_jwt=encode_jwt("notexists@email.com",["get:users","post:users"])
        res=self.client().get("/users/transactions",headers={"Authorization": f"Bearer {mock_jwt.decode('ASCII')}"})
        data=json.loads(res.data)
        self.assertTrue(res.status_code==404)
        self.assertTrue(data["message"]=="user does not exist")

        '''it should return transaction history'''
        i=1
        while(i<=20):
            UserTransactions("credit",'test2@email.com',i,True,
            datetime.utcnow().date().isoformat(),datetime.utcnow().time().isoformat(),
            'test@email.com').insert();i+=1

        res= self.client().get("/users/transactions?page=1",
        headers={"Authorization": f"Bearer {self.testjwt.decode('ASCII')}"})
        [transaction.delete() for transaction in UserTransactions.query.all()]
        data=json.loads(res.data)
        self.assertEqual(res.status_code,200)
        self.assertTrue(isinstance(data["transactions"],list))
        self.assertEqual(len(data["transactions"]),10)
        self.assertTrue(data["user"]=='test@email.com')

    


# Make the tests conveniently executable
if __name__ == "__main__":
    unittest.main()
