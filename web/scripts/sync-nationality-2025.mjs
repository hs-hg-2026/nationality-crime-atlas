import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseNationality2025 } from '../lib/nationality-2025.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const approved = () =>
  JSON.parse(
    readFileSync(
      resolve(root, 'config/publication/nationality_2025/latest.json'),
      'utf8',
    ),
  );

export function verifyNationality2025(
  directory = resolve(root, 'web/public/data'),
) {
  const pointer = approved();
  const bytes = readFileSync(resolve(directory, 'nationality_2025.json'));
  const manifest = JSON.parse(
    readFileSync(resolve(directory, 'nationality_2025.manifest.json'), 'utf8'),
  );
  const contractBytes = readFileSync(
    resolve(root, 'config/nationality_2025_contract.json'),
  );
  const contract = JSON.parse(contractBytes.toString('utf8'));
  const product = parseNationality2025(JSON.parse(bytes.toString('utf8')));
  if (
    digest(bytes) !== pointer.sha256 ||
    JSON.stringify(manifest) !== JSON.stringify(pointer) ||
    digest(contractBytes) !== pointer.contract_sha256 ||
    product.contract_sha256 !== pointer.contract_sha256 ||
    product.comparison.length !== pointer.comparison_count ||
    product.composition.length !== pointer.composition_count
  )
    throw new Error('2025 supplement differs from reviewed publication pins');
  for (const [id, pin] of Object.entries(contract.input_pins)) {
    if (
      product.sources[id].sha256 !== pin.artifact_sha256 ||
      product.sources[id].normalized_sha256 !== pin.normalized_sha256
    )
      throw new Error(`2025 input pin mismatch: ${id}`);
  }
  if (
    product.definitions.entities.join('|') !==
    contract.entities.map((e) => e.label).join('|')
  )
    throw new Error('2025 entity contract mismatch');
  return product;
}

function main() {
  if (!process.argv.includes('--verify')) {
    const pointer = approved();
    const generated = JSON.parse(
      readFileSync(
        resolve(root, 'output/nationality_2025/latest.json'),
        'utf8',
      ),
    );
    if (
      generated.sha256 !== pointer.sha256 ||
      generated.contract_sha256 !== pointer.contract_sha256 ||
      isAbsolute(generated.product_path) ||
      generated.product_path.split('/').includes('..') ||
      !generated.product_path.startsWith('output/nationality_2025/')
    )
      throw new Error('Generated supplement is not the reviewed version');
    const bytes = readFileSync(resolve(root, generated.product_path));
    if (digest(bytes) !== pointer.sha256)
      throw new Error('Generated supplement hash mismatch');
    parseNationality2025(JSON.parse(bytes.toString('utf8')));
    const target = resolve(root, 'web/public/data/nationality_2025.json');
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, bytes);
    writeFileSync(
      resolve(root, 'web/public/data/nationality_2025.manifest.json'),
      JSON.stringify(pointer, null, 2) + '\n',
    );
  }
  const product = verifyNationality2025();
  console.log(
    `2025 supplement verified: ${product.comparison.length} comparison rows, ${product.composition.length} composition rows`,
  );
}
if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)
  main();
