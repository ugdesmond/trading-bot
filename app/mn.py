import numpy as np
import string
import hmac
import hashlib


if __name__ == '__main__':
    length = 16
    a = np.random.choice(list(string.ascii_uppercase + string.digits+string.ascii_lowercase), length)
    print(''.join(a))

    text = b"This is a secret"
    texttt = b"This is a secret"
    signature = hmac.new(key=texttt, msg=text, digestmod=hashlib.sha384).hexdigest()
    print("HMAC is {}".format(signature))  # HMAC is 08dc7014b3e778a44af52ea7a16a973a9b48f0dd
