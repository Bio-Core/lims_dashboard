# helper function for setting multiple attributes with key-value pair
def setattrs(_self, **kwargs): 
    for k,v in kwargs.items(): setattr(_self, k, v)