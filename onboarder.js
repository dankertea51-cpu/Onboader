#!/usr/bin/env node
"use strict";

/*
 * Onboarder — AI-гид по кодовой базе. CLI + HTML-отчёт.
 *
 * Использование:
 *   node onboarder.js [/path/to/repo] [--out report.html] [--json]
 *
 * Запускает analyzer.py (лежит рядом), получает JSON-анализ и генерирует
 * самодостаточный HTML-отчёт: архитектура, ключевые файлы, эксперты,
 * команды запуска/тестов/деплоя, карта API и БД, чек-лист новичка.
 * Работает локально, без внешних сервисов. Нужны Node.js 14+ и Python 3.
 */

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const C = {
  reset: "\x1b[0m", bold: "\x1b[1m", dim: "\x1b[2m",
  green: "\x1b[32m", cyan: "\x1b[36m", yellow: "\x1b[33m", red: "\x1b[31m",
};

const PALETTE = ["#7c6ff0", "#3eb8a2", "#f0a35e", "#e36588",
  "#5ea9f0", "#b8cc5e", "#9a6ff0", "#f0d65e"];

const USAGE = `\nOnboarder — AI-гид по кодовой базе\n\n  node onboarder.js [путь к репозиторию] [опции]\n\nОпции:\n  --out <файл>   куда сохранить HTML-отчёт (по умолчанию onboarder-report.html в репозитории)\n  --json         вывести сырой JSON-анализ вместо HTML\n  -h, --help     эта справка\n`;

function parseArgs(argv) {
  const opts = { repo: process.cwd(), out: null, json: false, help: false };
  const rest = argv.slice(2);
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a === "--out" && rest[i + 1]) opts.out = path.resolve(rest[++i]);
    else if (a === "--json") opts.json = true;
    else if (a === "-h" || a === "--help") opts.help = true;
    else opts.repo = path.resolve(a);
  }
  if (!opts.out) opts.out = path.join(opts.repo, "onboarder-report.html");
  return opts;
}

function die(msg) {
  console.error(C.red + "✖ " + msg + C.reset);
  process.exit(1);
}

function findPython() {
  for (const bin of ["python3", "python"]) {
    const res = spawnSync(bin, ["--version"], { encoding: "utf8" });
    if (res.status === 0) return bin;
  }
  return null;
}

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/\"/g, "&quot;");
}

/* ----------------------------- HTML-отчёт ----------------------------- */

function langBarHtml(languages) {
  const total = languages.reduce((s, l) => s + l.lines, 0) || 1;
  const segs = languages.map((l, i) =>
    `<div title="${esc(l.name)}" style="width:${(100 * l.lines / total).toFixed(1)}%;background:${PALETTE[i % PALETTE.length]}"></div>`
  ).join("");
  const legend = languages.map((l, i) =>
    `<span class="lg"><i style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(l.name)} <b>${(100 * l.lines / total).toFixed(1)}%</b></span>`
  ).join("");
  return `<div class="bar">${segs}</div><div class="legend">${legend}</div>`;
}

function tableHtml(headers, rows) {
  const head = headers.map((h) => `<th>${esc(h)}</th>`).join("");
  const body = rows.map((r) =>
    `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function sectionHtml(title, inner) {
  return inner ? `<section><h2>${esc(title)}</h2>${inner}</section>` : "";
}

function commandsHtml(commands) {
  const labels = { setup: "Установка", run: "Запуск", test: "Тесты",
    deploy: "Деплой", other: "Прочее" };
  let html = "";
  for (const key of Object.keys(labels)) {
    const list = commands[key] || [];
    if (!list.length) continue;
    const items = list.map((c) =>
      `<li><code>${esc(c.cmd)}</code> <span class="src">${esc(c.source)}</span></li>`
    ).join("");
    html += `<div class="cmd-group"><h3>${labels[key]}</h3><ul>${items}</ul></div>`;
  }
  return html;
}

function buildHtml(data) {
  const mods = (data.modules || []).map((m) => [
    `<code>${esc(m.name)}</code>`,
    String(m.files),
    esc(m.language),
    (m.experts || []).map((e) => `${esc(e.name)} <span class="src">(${e.commits})</span>`).join(", ") || "—",
  ]);

  const keyFiles = (data.key_files || []).map((f) =>
    `<li><code>${esc(f.path)}</code>${f.changes ? ` <span class="src">${f.changes} изменений</span>` : ""}</li>`
  ).join("");

  const apiRows = (data.api || []).slice(0, 100).map((a) => [
    esc(a.framework),
    `<span class="method">${esc(a.method)}</span>`,
    `<code>${esc(a.path)}</code>`,
    `<span class="src">${esc(a.file)}</span>`,
  ]);

  const dbModels = ((data.db || {}).models || []).slice(0, 100).map((m) => [
    esc(m.kind), `<code>${esc(m.name)}</code>`, `<span class="src">${esc(m.file)}</span>`,
  ]);
  const mig = ((data.db || {}).migrations) || { count: 0, paths: [] };

  const contributors = (data.contributors || []).map((c) =>
    `<li>${esc(c.name)} <span class="src">${c.commits} коммитов</span></li>`
  ).join("");

  const checklist = (data.checklist || []).map((item) =>
    `<li><label><input type="checkbox"> <span>${esc(item)}</span></label></li>`
  ).join("");

  const stackChips = (data.stack || []).map((s) =>
    `<span class="chip" title="${esc(s.marker)}">${esc(s.label)}</span>`
  ).join("");

  return `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Onboarder · ${esc(data.name)}</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #15141a; color: #e6e4ef;
    font: 15px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 32px 20px 80px; }
  header h1 { margin: 0 0 4px; font-size: 28px; }
  header .meta { color: #8e8aa0; font-size: 13px; }
  .stats { display: flex; gap: 12px; margin: 18px 0 6px; flex-wrap: wrap; }
  .stat { background: #1f1d27; border: 1px solid #2c2937; border-radius: 10px;
    padding: 10px 16px; }
  .stat b { display: block; font-size: 20px; }
  .stat span { color: #8e8aa0; font-size: 12px; }
  section { background: #1b1922; border: 1px solid #2c2937; border-radius: 12px;
    padding: 18px 22px; margin-top: 18px; }
  h2 { margin: 0 0 12px; font-size: 18px; }
  h3 { margin: 10px 0 6px; font-size: 14px; color: #b9b5cc; }
  .bar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; }
  .legend { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px 16px;
    font-size: 13px; }
  .lg i { display: inline-block; width: 10px; height: 10px; border-radius: 3px;
    margin-right: 5px; }
  .chip { display: inline-block; background: #2a2735; border-radius: 14px;
    padding: 4px 12px; margin: 3px 4px 3px 0; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #2c2937; }
  th { color: #8e8aa0; font-weight: 600; }
  code { background: #2a2735; padding: 2px 6px; border-radius: 5px;
    font-size: 12.5px; }
  ul { margin: 6px 0; padding-left: 20px; }
  li { margin: 4px 0; }
  .src { color: #8e8aa0; font-size: 12px; }
  .method { color: #3eb8a2; font-weight: 700; font-size: 12px; }
  .cmd-group ul { list-style: none; padding-left: 0; }
  .checklist { list-style: none; padding-left: 0; }
  .checklist label { cursor: pointer; }
  .checklist input:checked + span { text-decoration: line-through; color: #8e8aa0; }
  footer { margin-top: 24px; color: #8e8aa0; font-size: 12px; text-align: center; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🧭 Onboarder · ${esc(data.name)}</h1>
    <div class="meta">${esc(data.repo)} · сгенерировано ${esc(data.generated_at)} за ${esc(data.elapsed_sec)} с</div>
    <div class="stats">
      <div class="stat"><b>${data.stats.files}</b><span>файлов</span></div>
      <div class="stat"><b>${data.stats.lines.toLocaleString("ru-RU")}</b><span>строк кода</span></div>
      <div class="stat"><b>${(data.modules || []).length}</b><span>модулей</span></div>
      <div class="stat"><b>${(data.api || []).length}</b><span>эндпоинтов API</span></div>
    </div>
  </header>

  ${sectionHtml("Языки", (data.languages || []).length ? langBarHtml(data.languages) : "")}
  ${sectionHtml("Стек и инструменты", stackChips)}
  ${sectionHtml("Архитектура: модули и эксперты", mods.length
    ? tableHtml(["Модуль", "Файлов", "Язык", "Эксперты"], mods) : "")}
  ${sectionHtml("Ключевые файлы", keyFiles ? `<ul>${keyFiles}</ul>` : "")}
  ${sectionHtml("Как запускать, тестировать и деплоить", commandsHtml(data.commands || {}))}
  ${sectionHtml("Карта API", apiRows.length
    ? tableHtml(["Фреймворк", "Метод", "Путь", "Файл"], apiRows) : "")}
  ${sectionHtml("База данных",
    (dbModels.length || mig.count)
      ? (mig.count ? `<p>Миграций: <b>${mig.count}</b> (${mig.paths.map(esc).join(", ")})</p>` : "")
        + (dbModels.length ? tableHtml(["Тип", "Модель / таблица", "Файл"], dbModels) : "")
      : "")}
  ${sectionHtml("Главные контрибьюторы", contributors ? `<ul>${contributors}</ul>` : "")}
  ${sectionHtml("Чек-лист новичка", checklist ? `<ul class="checklist">${checklist}</ul>` : "")}

  <footer>Сгенерировано Onboarder локально · без внешних сервисов</footer>
</div>
<script>
(function () {
  var key = "onboarder-checklist:" + document.title;
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) {}
  var boxes = document.querySelectorAll(".checklist input");
  Array.prototype.forEach.call(boxes, function (box, i) {
    if (saved[i]) box.checked = true;
    box.addEventListener("change", function () {
      saved[i] = box.checked;
      try { localStorage.setItem(key, JSON.stringify(saved)); } catch (e) {}
    });
  });
})();
</script>
</body>
</html>
`;
}

/* --------------------------- Сводка в консоль -------------------------- */

function printSummary(data, outPath, seconds) {
  const log = console.log;
  log("");
  log(`${C.bold}${C.green}✔ Готово за ${seconds.toFixed(1)} с${C.reset}`);
  log(`${C.bold}🧭 ${data.name}${C.reset} ${C.dim}(${data.repo})${C.reset}`);
  log(`   Файлов: ${data.stats.files} · строк: ${data.stats.lines} · модулей: ${(data.modules || []).length} · эндпоинтов: ${(data.api || []).length}`);
  const langs = (data.languages || []).slice(0, 3).map((l) => l.name).join(", ");
  if (langs) log(`   Языки: ${langs}`);
  const stack = (data.stack || []).map((s) => s.label).join(", ");
  if (stack) log(`   Стек: ${stack}`);
  const experts = (data.contributors || []).slice(0, 3)
    .map((c) => `${c.name} (${c.commits})`).join(", ");
  if (experts) log(`   Эксперты: ${experts}`);
  log(`   Чек-лист новичка: ${(data.checklist || []).length} шагов`);
  log("");
  log(`${C.cyan}▸ Отчёт: ${outPath}${C.reset}`);
  log(`${C.dim}  Откройте файл в браузере, чтобы начать тур.${C.reset}`);
}

/* --------------------------------- main -------------------------------- */

function main() {
  const opts = parseArgs(process.argv);
  if (opts.help) { console.log(USAGE); return; }
  if (!fs.existsSync(opts.repo)) die("Каталог не найден: " + opts.repo);

  const py = findPython();
  if (!py) die("Python 3 не найден. Установите python3 и повторите.");

  const analyzer = path.join(__dirname, "analyzer.py");
  if (!fs.existsSync(analyzer)) die("Рядом с onboarder.js нет analyzer.py");

  console.log(`${C.cyan}▸ Анализирую ${opts.repo} ...${C.reset}`);
  const t0 = Date.now();
  const res = spawnSync(py, [analyzer, opts.repo],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (res.error) die("Не удалось запустить анализатор: " + res.error.message);
  if (res.status !== 0) {
    die("Анализатор завершился с ошибкой:\n" + (res.stderr || res.stdout || ""));
  }

  let data;
  try {
    data = JSON.parse(res.stdout);
  } catch (e) {
    die("Не удалось разобрать вывод анализатора: " + e.message);
  }
  if (data.error) die(data.error);

  if (opts.json) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  fs.writeFileSync(opts.out, buildHtml(data), "utf8");
  printSummary(data, opts.out, (Date.now() - t0) / 1000);
}

main();
