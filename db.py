import motor.motor_asyncio
import urllib.parse
from schema import CustomerSchema, Address, AccountSchema
from datetime import date, datetime
from utility import random_with_N_digits
from fastapi.encoders import jsonable_encoder
from dateutil.relativedelta import relativedelta

username = urllib.parse.quote_plus('poc_fastapi')
password = urllib.parse.quote_plus("poc@fastapi")

MONGO_DETAILS = "mongodb+srv://{}:{}@cluster0.o7fdi.mongodb.net/bankdb?retryWrites=true&w=majority".format(
    username, password)

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.bankdb

accounts_collection = database.get_collection("accounts_collection")
customers_collection = database.get_collection("customers_collection")


def customer_helper(customer) -> dict:
    return {
        "account_holder_name": customer["account_holder_name"],
        "aadhaar": customer["aadhaar"],
        "contact": customer["contact"],
        "email": customer["email"],
        "pan": customer["pan"],
        "address": customer["address"],
        "dob": customer["dob"],
    }


def account_helper(account) -> dict:
    return {
        "account_number": account["account_number"],
        "created_date": account["created_date"],
        "branch_name": account["branch_name"],
        "ifsc_code": account["ifsc_code"],
        "bank_name": account["bank_name"],
        "account_type": account["account_type"],
        "aadhaar": account["aadhaar"],
        "balance": account["balance"],
        "last_activity": account["last_activity"],
        "is_active": account["is_active"]
    }


async def does_account_exists_for_customer(customer_details: CustomerSchema):
    existing_customer = await accounts_collection.find_one({"aadhaar": customer_details.aadhaar})
    print(existing_customer)
    if existing_customer:
        return True
    return False


async def get_account_details(search_key: str, search_value: str):
    account = await accounts_collection.find_one({search_key: search_value})
    print("Account - ", account)
    if account:
        return True, account
    return False, None


async def create_customer_and_account(customer_details: CustomerSchema):
    account_details = AccountSchema()
    account_details.aadhaar = customer_details["aadhaar"]
    today = date.today()
    account_details.created_date = today.strftime("%d/%m/%Y")
    account_details.branch_name = "GACHIBOWLI"
    account_details.ifsc_code = "AAAA1234"
    account_details.bank_name = "QWERTY"
    account_details.account_type = "SAVINGS"
    account_details.balance = 0

    now = datetime.now()
    last_activity = now.strftime("%d/%m/%Y %H:%M:%S")

    account_details.last_activity = last_activity
    account_details.is_active = True

    account_number_temp = str(random_with_N_digits(10))
    existing_account_numbers = set()

    async for account in accounts_collection.find():
        if "account_number" in account:
            existing_account_numbers.add(account["account_number"])

    while account_number_temp in existing_account_numbers:
        account_number_temp = str(random_with_N_digits(10))

    account_details.account_number = account_number_temp

    new_customer = await customers_collection.insert_one(customer_details)
    new_account = await accounts_collection.insert_one(jsonable_encoder(account_details))

    new_customer = await customers_collection.find_one({"_id": new_customer.inserted_id})
    new_account = await accounts_collection.find_one({"_id": new_account.inserted_id})

    return customer_helper(new_customer), account_helper(new_account)


async def get_account_balance(account_number: str):
    account_exists, account = await get_account_details("account_number", account_number)
    if account_exists:
        await update_last_activity(account_number)
        return True, account["balance"]
    return False, 0


async def update_balance(account_number: str, amount: int, available_balance: int, operation_type: str):
    query = {'account_number': account_number}

    if operation_type == "DEPOSIT":
        updated_balance = {"$set": {'balance': available_balance + amount}}
        await accounts_collection.update_one(query, updated_balance)
        updated_balance = await get_account_balance(account_number)
        print("Account balance after updating balance - ", updated_balance[1])
    elif operation_type == "WITHDRAW":
        updated_balance = {"$set": {'balance': available_balance - amount}}
        await accounts_collection.update_one(query, updated_balance)
        updated_balance = await get_account_balance(account_number)
        print(f"Account balance after withdrawing {amount} - ", updated_balance[1])

    await update_last_activity(account_number)
    return updated_balance[1]


async def update_last_activity(account_number: str):
    query = {"account_number": account_number}
    now = datetime.now()
    last_activity = now.strftime("%d/%m/%Y %H:%M:%S")
    updated_activity = {"$set": {'last_activity': last_activity}}
    await accounts_collection.update_one(query, updated_activity)


async def delete_invalid_accounts():
    deactivated_accounts = list()
    async for account in accounts_collection.find():
        account_last_activity = account["last_activity"]
        date_format = "%d/%m/%Y %H:%M:%S"
        account_last_activity = datetime.strptime(account_last_activity, date_format)
        now = datetime.now()
        valid_date = now - relativedelta(minutes=1)

        if account_last_activity < valid_date:
            account_number = account["account_number"]
            is_account_active = account["is_active"]
            query = {"account_number": account_number}
            update_query = {"$set": {'is_active': False}}
            if is_account_active:
                await accounts_collection.update_one(query, update_query)
                deactivated_accounts.append(account_number)

    return deactivated_accounts
