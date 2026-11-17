/*
 * Ridgeline Trail Club | production build (Week 4)
 *
 *   src/  readable source you edit
 *   dist/ what you deploy
 *
 * What it does
 *   1. Optimises the SVG images (SVGO)
 *   2. Minifies CSS (Lightning CSS), JavaScript (esbuild) and HTML (html-minifier-terser)
 *   3. Inlines critical.css into <head>; loads main.css without blocking rendering
 *   4. Gives every asset a content hash in its file name, so it can be cached for a year
 *   5. Writes caching headers and a size report (raw / gzip / brotli)
 *
 * Run:  npm install && npm run build
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gzipSync, brotliCompressSync, constants } from 'node:zlib';
import { join, basename } from 'node:path';
import { transform } from 'lightningcss';
import { transform as esbuild } from 'esbuild';
import { minify as minifyHtml } from 'html-minifier-terser';
import { optimize } from 'svgo';

const SRC = new URL('./src/', import.meta.url).pathname;
const STRATEGY = process.env.CSS_STRATEGY || 'async'; // async | blocking | inline
const DIST = new URL(`./${process.env.OUT || 'dist'}/`, import.meta.url).pathname;
const ASSETS = join(DIST, 'assets');
const read = (p) => readFileSync(join(SRC, p), 'utf8');
const hash = (buf) => createHash('sha256').update(buf).digest('hex').slice(0, 8);
const sizes = (buf) => ({
  raw: buf.length,
  gzip: gzipSync(buf, { level: 9 }).length,
  brotli: brotliCompressSync(buf, { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } }).length,
});

rmSync(DIST, { recursive: true, force: true });
mkdirSync(ASSETS, { recursive: true });

const report = { files: {}, before: {} };
const map = {}; // source path -> final path (relative to dist/)

function emit(srcName, ext, content, label) {
  const buf = Buffer.isBuffer(content) ? content : Buffer.from(content);
  const name = `${basename(srcName, ext)}.${hash(buf)}${ext}`;
  writeFileSync(join(ASSETS, name), buf);
  map[srcName] = `assets/${name}`;
  report.files[label || srcName] = sizes(buf);
  return name;
}

/* 1. Images: SVGO */
for (const f of readdirSync(join(SRC, 'images'))) {
  const original = readFileSync(join(SRC, 'images', f), 'utf8');
  const out = optimize(original, {
    multipass: true,
    // preset-default also runs removeMetadata, which drops the embedded <metadata> block
    // (here: a ~7.9 KB content-credentials manifest per file). The untouched originals stay in src/images.
    plugins: ['preset-default', 'removeDimensions'],
  }).data;
  report.before['images/' + f] = sizes(Buffer.from(original));
  emit('images/' + f, '.svg', out, 'images/' + f);
}

/* 2. Fonts: already subset; just hash and copy */
for (const f of readdirSync(join(SRC, 'fonts'))) {
  const buf = readFileSync(join(SRC, 'fonts', f));
  report.before['fonts/' + f] = { raw: buf.length };
  emit('fonts/' + f, '.woff2', buf, 'fonts/' + f);
}
{
  const original = readFileSync(join(SRC, 'favicon.svg'), 'utf8');
  const out = optimize(original, { multipass: true, plugins: ['preset-default', 'removeDimensions'] }).data;
  report.before['favicon.svg'] = sizes(Buffer.from(original));
  writeFileSync(join(DIST, 'favicon.svg'), out);
  report.files['favicon.svg'] = sizes(Buffer.from(out));
}

/* 3. CSS */
const minCss = (code, filename) =>
  transform({
    filename, code: Buffer.from(code), minify: true,
    targets: { chrome: 105 << 16, safari: (15 << 16) | (4 << 8), firefox: 121 << 16 },
  }).code.toString();

let critical = read('css/critical.css');
report.before['css/critical.css'] = sizes(Buffer.from(critical));
const criticalInline = minCss(critical, 'critical.css').replace(/\.\.\/fonts\/([\w-]+)\.woff2/g, (_, n) => map[`fonts/${n}.woff2`]);
const criticalFile = minCss(critical, 'critical.css').replace(/\.\.\/fonts\/([\w-]+)\.woff2/g, (_, n) => map[`fonts/${n}.woff2`].replace('assets/', ''));
report.files['css/critical.css (inlined)'] = sizes(Buffer.from(criticalInline));

const main = read('css/main.css');
report.before['css/main.css'] = sizes(Buffer.from(main));
const mainInline = minCss(main, 'main.css');
emit('css/main.css', '.css', mainInline);
emit('css/critical.css', '.css', criticalFile); // used by policies.html, which is a plain blocking page

/* 4. JavaScript */
const js = read('js/script.js');
report.before['js/script.js'] = sizes(Buffer.from(js));
emit('js/script.js', '.js', (await esbuild(js, { minify: true, target: 'es2020', legalComments: 'none' })).code);

/* 5. HTML */
const htmlOptions = {
  collapseWhitespace: true, conservativeCollapse: true, collapseBooleanAttributes: true,
  removeComments: true, minifyJS: true  /* keep type="text" etc: explicit is valid and safer */, sortAttributes: false,
};
const rewrite = (html) => html.replace(/(href|src|srcset)="((?:fonts|images|js|css)\/[^"]+)"/g, (m, attr, p) => (map[p] ? `${attr}="${map[p]}"` : m));

async function page(file, { inlineCritical }) {
  let html = read(file);
  report.before[file] = sizes(Buffer.from(html));
  if (inlineCritical) {
    const mainHref = map['css/main.css'];
    if (STRATEGY === 'async') {
      // critical CSS inline; the rest loads without blocking the first paint
      html = html.replace(/<!-- critical:start -->[\s\S]*?<!-- critical:end -->/, `<style>${criticalInline}</style>`);
      html = html.replace(/<!-- deferred:start -->[\s\S]*?<!-- deferred:end -->/,
        `<link rel="preload" href="${mainHref}" as="style" onload="this.onload=null;this.rel='stylesheet'"><noscript><link rel="stylesheet" href="${mainHref}"></noscript>`);
    } else if (STRATEGY === 'inline') {
      // all CSS inline: no CSS request at all
      html = html.replace(/<!-- critical:start -->[\s\S]*?<!-- critical:end -->/, `<style>${criticalInline}${mainInline}</style>`);
      html = html.replace(/<!-- deferred:start -->[\s\S]*?<!-- deferred:end -->/, '');
    } else {
      // blocking: two normal stylesheets (the simple baseline for comparison)
      html = html.replace(/<!-- critical:start -->[\s\S]*?<!-- critical:end -->/, `<link rel="stylesheet" href="${map['css/critical.css']}">`);
      html = html.replace(/<!-- deferred:start -->[\s\S]*?<!-- deferred:end -->/, `<link rel="stylesheet" href="${mainHref}">`);
    }
  }
  html = rewrite(html);
  // pages that keep their stylesheet links also need hashed names
  html = html.replace('href="css/critical.css"', `href="${map['css/critical.css']}"`).replace('href="css/main.css"', `href="${map['css/main.css']}"`);
  const out = await minifyHtml(html, htmlOptions);
  writeFileSync(join(DIST, file), out);
  report.files[file] = sizes(Buffer.from(out));
}
await page('index.html', { inlineCritical: true });
await page('policies.html', { inlineCritical: false });

/* 6. Caching headers for common hosts */
writeFileSync(join(DIST, '_headers'), `# Netlify / Cloudflare Pages
/assets/*
  Cache-Control: public, max-age=31536000, immutable
/favicon.svg
  Cache-Control: public, max-age=86400
/*.html
  Cache-Control: no-cache
/
  Cache-Control: no-cache
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
`);
writeFileSync(join(DIST, '.htaccess'), `# Apache: compression + caching
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css application/javascript image/svg+xml
</IfModule>
<IfModule mod_headers.c>
  <FilesMatch "\\.(css|js|woff2|svg)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
  <FilesMatch "\\.html$">
    Header set Cache-Control "no-cache"
  </FilesMatch>
  Header set X-Content-Type-Options "nosniff"
</IfModule>
`);

writeFileSync(new URL('./tests/build-report.json', import.meta.url), JSON.stringify(report, null, 1));
const total = Object.entries(report.files).filter(([k]) => !k.includes('inlined')).reduce((a, [, v]) => ({ raw: a.raw + v.raw, gzip: a.gzip + v.gzip, brotli: a.brotli + v.brotli }), { raw: 0, gzip: 0, brotli: 0 });
console.table(Object.fromEntries(Object.entries(report.files).map(([k, v]) => [k, v])));
console.log('TOTAL (deployed files)', total);
