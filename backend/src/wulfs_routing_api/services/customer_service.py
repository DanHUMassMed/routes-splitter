import re
import pandas as pd
from wulfs_routing_api.models.customers.customer_model import CustomerModel

class CustomerService():
    def __init__(self, model: CustomerModel):
        self.model = model

    def load_customer_master_data(self):
        customer_master_df  = self.model.get_all_customers()
        return customer_master_df
        
    
