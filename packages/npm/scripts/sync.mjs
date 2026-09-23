// Copies schemas/v1/ and vectors/ from the repository root into this package, so
// the published package carries the protocol revision it was built from. The
// copies are ignored by git; the repository root stays the only source.
import { cpSync, existsSync, rmSync } from "node:fs";
import { URL, fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const pkg = fileURLToPath(new URL("../", import.meta.url));

for (const dir of ["schemas/v1", "vectors"]) {
  if (!existsSync(root + dir)) {
    throw new Error(`sync: ${root + dir} not found; run in a repository clone`);
  }
  rmSync(pkg + dir.split("/")[0], { recursive: true, force: true });
  cpSync(root + dir, pkg + dir, { recursive: true });
}
