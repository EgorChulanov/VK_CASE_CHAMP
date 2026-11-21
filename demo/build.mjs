import { build } from "esbuild";
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";

const outdir = "dist";
await mkdir(outdir, { recursive: true });
await cp("public", outdir, { recursive: true });
await build({
  entryPoints: ["shop.jsx"],
  outfile: outdir + "/shop.js",
  bundle: true,
  minify: true,
  format: "esm",
  target: "es2022",
  define: { "process.env.NODE_ENV": '"production"' },
  external: ["*.woff2", "*.webp"],
  loader: { ".svg": "dataurl", ".png": "dataurl" },
});
const template = await readFile("index.html", "utf8");
await writeFile(
  outdir + "/index.html",
  template.replace('src="./shop.jsx"', 'src="./shop.js"').replace("</title>", '</title><link rel="stylesheet" href="./shop.css">'),
);
