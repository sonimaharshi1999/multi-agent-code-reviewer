# Multi-Agent Code Review System -- Test Fixture
# Author: Maharshi Soni | License: MIT
"""Synthetic vulnerable code for testing the SecurityAgent."""

import os
import pickle
import subprocess


# Dangerous: eval with user input
def run_user_expression(expr):
    return eval(expr)


# Dangerous: exec
def dynamic_execute(code_string):
    exec(code_string)


# Dangerous: os.system (shell injection)
def ping_host(host):
    os.system(f"ping -c 1 {host}")


# Hardcoded secret
API_KEY = "sk-super-secret-key-12345"
password = "hunter2"


# SQL injection via f-string
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query


# subprocess with shell=True
def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout


# Pickle load (deserialization attack)
def load_data(data_bytes):
    return pickle.loads(data_bytes)
