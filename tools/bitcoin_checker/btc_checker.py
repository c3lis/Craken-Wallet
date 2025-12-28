import bip32utils
import mnemonic
import requests

# Generar una dirección Bitcoin a partir de un mnemonic
def get_bitcoin_address(seed):
    # Derivación estándar de BIP44 para Bitcoin: m/44'/0'/0'/0/0
    bip32_node = bip32utils.BIP32Key.fromEntropy(seed)
    bip32_child = bip32_node.ChildKey(44 + bip32utils.BIP32_HARDENED).ChildKey(0 + bip32utils.BIP32_HARDENED).ChildKey(0 + bip32utils.BIP32_HARDENED).ChildKey(0).ChildKey(0)

    # Obtener la clave pública y la dirección
    public_key = bip32_child.PublicKey().hex()
    address = bip32utils.public_key_to_address(public_key)

    return address

# Función para obtener el balance de la dirección
def get_balance(address):
    url = f'https://blockchain.info/q/addressbalance/{address}'
    response = requests.get(url)
    return response.text

# Obtener el mnemonic de la semilla
mnemonic_phrase = "your mnemonic phrase here"
mnemonic_obj = mnemonic.Mnemonic("english")
seed = mnemonic_obj.to_seed(mnemonic_phrase)

# Generar la dirección
address = get_bitcoin_address(seed)
print(f'Dirección Bitcoin generada: {address}')

# Consultar el saldo de la dirección
balance = get_balance(address)
print(f'Balance de la dirección {address}: {balance} satoshis')
