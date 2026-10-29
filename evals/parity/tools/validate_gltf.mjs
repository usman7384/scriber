import { readFileSync } from "node:fs";
import { validateBytes } from "gltf-validator";

const report = await validateBytes(new Uint8Array(readFileSync(process.argv[2])));
console.log(JSON.stringify(report));
