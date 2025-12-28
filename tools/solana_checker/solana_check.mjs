// check_solana_from_file.mjs
import { Connection, Keypair, clusterApiUrl } from '@solana/web3.js';
import * as bip39 from 'bip39';
import { derivePath } from 'ed25519-hd-key';
import fs from 'fs/promises';
import process from 'process';
import { argv } from 'process';

const DEFAULT_WORDLIST = 'mnemonics.txt';
const DEFAULT_OUTPUT = 'solana_results.txt';
const DEFAULT_FOUND = 'found_with_balance.txt';
const DERIVATION_PATH = "m/44'/501'/0'/0'";

// ANSI colors
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const GREEN = '\x1b[32m';
const RESET = '\x1b[0m';

// --- utils ---
function parseArgs() {
  const args = argv.slice(2);
  const res = {
    wordlist: args[0] ?? DEFAULT_WORDLIST,
    outFile: args[1] ?? DEFAULT_OUTPUT,
    foundFile: args[2] ?? DEFAULT_FOUND,
    concurrency: 7,
    delay: 200,
    rpc: 'mainnet-beta'
  };

  // parse named flags
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--concurrency' && args[i+1]) res.concurrency = Math.max(1, parseInt(args[i+1], 10));
    if (args[i] === '--delay' && args[i+1]) res.delay = Math.max(0, parseInt(args[i+1], 10));
    if (args[i] === '--rpc' && args[i+1]) res.rpc = args[i+1];
  }
  return res;
}

async function loadMnemonics(filePath) {
  const raw = await fs.readFile(filePath, { encoding: 'utf8' });
  return raw
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l && !l.startsWith('#'));
}

// append serialized to avoid interleaving writes
let appendChain = Promise.resolve();
function appendLineSerialized(file, line) {
  appendChain = appendChain.then(() => fs.appendFile(file, line + '\n', { encoding: 'utf8' }));
  return appendChain;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// --- processing ---
async function processMnemonic(mnemonic, connection, outFile, foundFile) {
  try {
    const seed = await bip39.mnemonicToSeed(mnemonic); // Buffer
    const { key } = derivePath(DERIVATION_PATH, seed.toString('hex'));
    const keypair = Keypair.fromSeed(key);
    const pubKey = keypair.publicKey;
    const address = pubKey.toBase58();

    const lamports = await connection.getBalance(pubKey);
    const sol = lamports / 1e9;
    const timestamp = new Date().toISOString();
    const line = `${timestamp} | ADDRESS: ${address} | SOL: ${sol} | MNEMONIC: ${mnemonic}`;

    // siempre guardamos en el log general (append serializado)
    await appendLineSerialized(outFile, line);

    if (sol > 0) {
      const foundLine = `${timestamp} | MNEMONIC: ${mnemonic} | ADDRESS: ${address} | SOL: ${sol}`;
      // print highlighted in red and also write to found file
      console.log(RED + 'FOUND -> ' + foundLine + RESET);
      await appendLineSerialized(foundFile, foundLine);
    } else {
      console.log(YELLOW + `CHECK -> ADDRESS: ${address} | SOL: ${sol}` + RESET);
    }
  } catch (err) {
    const timestamp = new Date().toISOString();
    const line = `${timestamp} | ERROR procesando mnemonic (${mnemonic.slice(0,20)}...): ${err.message}`;
    console.error(line);
    await appendLineSerialized(outFile, line);
  }
}

// --- worker queue pattern ---
async function runWorkers(mnemonics, connection, outFile, foundFile, concurrency, delay) {
  let nextIndex = 0;
  const total = mnemonics.length;

  async function worker(id) {
    while (true) {
      const i = nextIndex++;
      if (i >= total) break;
      const m = mnemonics[i];
      console.log(GREEN + `[Worker ${id}] [${i+1}/${total}]` + RESET);
      await processMnemonic(m, connection, outFile, foundFile);
      if (delay > 0) await sleep(delay);
    }
  }

  const workers = [];
  for (let w = 0; w < concurrency; w++) {
    workers.push(worker(w+1));
  }
  await Promise.all(workers);
}

// --- main ---
async function main() {
  const opts = parseArgs();
  const { wordlist, outFile, foundFile, concurrency, delay, rpc } = opts;

  try {
    await fs.access(wordlist);
  } catch {
    console.error(`No se encontró el archivo de wordlist: ${wordlist}`);
    process.exit(1);
  }

  const mnemonics = await loadMnemonics(wordlist);
  if (mnemonics.length === 0) {
    console.log('No hay mnemonics para procesar en el archivo.');
    return;
  }

  const connection = new Connection(clusterApiUrl(rpc), 'confirmed');

  console.log(`Procesando ${mnemonics.length} mnemonics con concurrency=${concurrency}, delay=${delay}ms en RPC=${rpc}`);
  await appendLineSerialized(outFile, `--- Inicio ${new Date().toISOString()} ---`);
  await appendLineSerialized(foundFile, `--- Inicio ${new Date().toISOString()} ---`);

  // ejecuta los "workers" asíncronos
  await runWorkers(mnemonics, connection, outFile, foundFile, concurrency, delay);

  await appendLineSerialized(outFile, `--- Fin ${new Date().toISOString()} ---\n`);
  await appendLineSerialized(foundFile, `--- Fin ${new Date().toISOString()} ---\n`);
  console.log('Proceso terminado.');
}

main().catch(err => {
  console.error('Fallo en el script:', err);
  process.exit(1);
});
