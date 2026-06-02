def get_customer_data(customer_id, customers, transactions, exceptions):

    customer_row = customers[customers["customer_id"] == customer_id]

    if customer_row.empty:
        return None

    customer_txns = transactions[transactions["customer_id"] == customer_id]
    customer_exceptions = exceptions[exceptions["customer_id"] == customer_id]

    return {
        "customer": customer_row.iloc[0].to_dict(),
        "transactions": customer_txns.to_dict(orient="records"),
        "exceptions": customer_exceptions.to_dict(orient="records")
    }