import { ethers } from "ethers";

// Ingresa tu frase semilla de 12 palabras aquí
const mnemonic = "insane area frozen hurt outside resist large found october mom earn dad";

// Crea un HDNode usando la frase semilla
const hdNode = ethers.utils.HDNode.fromMnemonic(mnemonic);

// Deriva la primera dirección Ethereum usando el camino BIP-44 estándar
const path = "m/44'/60'/0'/0/0";  // Camino de derivación para la primera cuenta Ethereum
const wallet = hdNode.derivePath(path);

// Muestra la dirección de la wallet
const address = wallet.address;  // Usamos wallet.address para obtener la dirección
console.log("Dirección de Ethereum:", address);
