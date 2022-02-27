import json
import traceback
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from schema import CustomerSchema
import logging
from fastapi.encoders import jsonable_encoder
from db import (
    does_account_exists_for_customer,
    create_customer_and_account,
    get_account_balance,
    get_account_details,
    account_helper,
    update_balance,
    delete_invalid_accounts
)

logging.basicConfig()

app = FastAPI(
    title="Banking API",
    version="1.0.0",
    docs_url="/",
    redoc_url="/docs"
)


def ResponseModel(data, status_code, message):
    return {
        "data": [data],
        "code": status_code,
        "message": message,
    }


@app.post("/create_account", response_description="Acount created successfully")
async def create_account(account_holder_details: CustomerSchema = Body(...)):
    try:
        if await does_account_exists_for_customer(account_holder_details):
            return JSONResponse(status_code=409, content={
                "account_holder_details": jsonable_encoder(account_holder_details),
                "message": f"Customer already has account registered under Aadhaar {account_holder_details.aadhaar}"
            })
        new_customer, new_account = await create_customer_and_account(jsonable_encoder(account_holder_details))
        logging.info("Created account")
        return JSONResponse(status_code=200, content={
            "account_holder_details": jsonable_encoder(new_customer),
            "account_details": jsonable_encoder(new_account),
            "message": f"Account has been created under Aadhaar {account_holder_details.aadhaar}"
        })
    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()


@app.post("/get_account_details", response_description="Retrieved Account details")
async def get_details(account_number: str):
    try:
        account_exists, account = await get_account_details("account_number", account_number)
        if account_exists:
            return JSONResponse(status_code=200, content=account_helper(account))
        return JSONResponse(status_code=404, content={
            "message": f"Account does not exist with account number {account_number}.Please recheck your account number."
        })
    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "message": f"Error occurred while trying to fetch the account details with account number {account_number}."
        })


@app.post("/get_account_balance", response_description="Retrieved account balance")
async def get_balance(account_number: str):
    try:
        account_exists, balance = await get_account_balance(account_number)
        if account_exists:
            return JSONResponse(status_code=200, content=balance)
        return JSONResponse(status_code=404, content={
            "message": f"Account does not exist with account number {account_number}.Please recheck your account number."
        })
    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "message": f"Error occurred while trying to fetch the account balance with account number {account_number}."
        })


@app.post("/deposit_amount", response_description="Amout deposited")
async def deposit(account_number: str, amount: int):
    try:
        account_exists, account = await get_account_details("account_number", account_number)
        if account_exists:
            updated_account_balance = await update_balance(account_number, amount, account_helper(account)["balance"],
                                                           "DEPOSIT")
            return JSONResponse(
                status_code=200,
                content={
                    "updated_balance": updated_account_balance,
                    "message": f"{amount} deposited into your account",
                })
        elif not account["is_active"]:
            return JSONResponse(
                status_code=200, content={
                    "message": f"Your account {account_number} is de-activated. Cannot deposit amount now."
                })
        return JSONResponse(
            status_code=404, content={
                "message": f"Account does not exist with account number {account_number}."
                           f"Please recheck your account number."
            })
    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "message": f"Error occurred while trying to deposit {amount} to the account with account number "
                       f"{account_number}."
        })


@app.post("/withdraw_amount", response_description="Amount withdrawn")
async def withdraw(account_number: str, amount: int):
    try:
        if amount % 500 != 0 or amount % 2000 != 0:
            return JSONResponse(status_code=400, content={"message": f"Invalid amount provided {amount}."
                                                                     f"please provide amount to be withdrawn "
                                                                     f"in multiples of 500 / 2000"})
        account_data = await get_account_balance(account_number)
        if account_data[0]:
            available_balance = account_data[1]

            if available_balance < 3000:
                return JSONResponse(status_code=406, content={"message": f"Insufficient funds . Available Balance- {available_balance}"})

            if available_balance - amount < 3000:
                return JSONResponse(status_code=406, content={"message": f"Insufficient funds - cannot withdraw more "
                                                                         f"than {available_balance - amount}."})

            updated_account_balance = await update_balance(account_number, amount, available_balance, "WITHDRAW")

            return JSONResponse(
                status_code=200,
                content={
                    "updated_balance": updated_account_balance,
                    "message": f"{amount} withdrawn from your account",
                })

    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "message": f"Error occurred while trying to withdraw {amount} from account with account number "
                       f"{account_number}."
        })


@app.post("/transfer_amount", response_description="Amount transferred")
async def transfer_amount(source_account_number: str, destination_account_number: str, amount: int):
    try:
        source_account_data = await get_account_balance(source_account_number)
        destination_account_data = await get_account_balance(destination_account_number)

        if not source_account_data[0]:
            return JSONResponse(status_code=404, content={
                "message": f"Source account does not exist with account number {source_account_number}.Please recheck source account number."})
        elif not destination_account_data[0]:
            return JSONResponse(status_code=404, content={
                "message": f"Destination account does not exist with account number {destination_account_number}.Please recheck destination account number."})

        if source_account_data[0]:
            source_available_balance = source_account_data[1]

            if source_available_balance < 3000:
                return JSONResponse(status_code=406,
                                    content={"message": f"Insufficient funds - {source_available_balance}"})

            if source_available_balance - amount < 3000:
                return JSONResponse(status_code=406, content={
                    "message": f"Insufficient funds - cannot transfer more than {source_available_balance - amount}."})

            source_updated_balance = await update_balance(source_account_number, amount, source_available_balance,
                                                          "WITHDRAW")
            destination_updated_balance = await update_balance(destination_account_number, amount, destination_account_data[1], "DEPOSIT")

            return JSONResponse(status_code=200, content={"updated_balance": source_updated_balance,
                                                          "message": f"Transferred {amount} from {source_account_number} to {destination_account_number}"})
    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "message": f"Error occurred while transferring amount {amount} from {source_account_number} to {destination_account_number}"})


@app.post("/delete_accounts")
async def deactivate_accounts():
    try:
        deactivated_accounts = await delete_invalid_accounts()
        return JSONResponse(status_code=200, content=deactivated_accounts)
    except Exception as exception:
        logging.error(exception)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": f"Error occurred while soft deleting the accounts"})
