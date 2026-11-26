/*
 * tracker:view のページの描画。テンプレート（table.html・kanban.html・detail.html）から、runtime.js より先に読み込まれる。
 * 印の JSON とテンプレートの data-ipt の印から描画だけを受け持つ。取り直し・誤りの扱い・状態は runtime.js が受け持つ。
 * 2つの受け渡しは window.iptView の1つの名前空間だけで行う（ここで作り、runtime.js が使う）。印の JSON の形と型ごとの印は
 * ../references/display-format.md の「テンプレート」にある。
 * 安全の決まり: 値はすべて textContent で文字として出し、リンクにするのは https:// で始まる URL だけにする。
 * 値をキーにする表は Map か Object.create(null) にし、引き当ては hasOwn にする（"__proto__"・"constructor" などの値で崩れないため）。
 */
(function () {
  "use strict";

  var FIELDS = ["キー", "タイトル", "状態", "担当", "種類", "ラベル", "更新日", "URL", "トラッカー"];
  var MULTI = { "担当": true, "ラベル": true };
  var COMMON_MARKS = ["title", "count", "updated", "refresh", "failures", "notes", "body"];
  var KINDS = {
    "表": ["group", "group-name", "head", "rows"],
    "カンバン": ["column", "column-name", "column-count", "cards", "card", "fields", "field", "label", "value"],
    "詳細": ["item", "item-title", "fields", "field", "label", "value", "item-body", "text", "item-children", "children",
      "item-comments", "comments"]
  };
  var PROTOTYPES = ["group", "column", "card", "field", "item"];  // <template> に置く雛形の印。ほかの型の印は雛形の中に置く
  // 印を付けてはいけない要素（textContent で入れた値がコード・CSS・読み込みとして働くもの、雛形でない <template>）。
  // HTML の名前空間の外（SVG の <script>・<style> など）にも付けない。
  var HTML_NS = "http://www.w3.org/1999/xhtml";
  var UNMARKABLE = ["SCRIPT", "STYLE", "IFRAME", "FRAME", "FRAMESET", "OBJECT", "EMBED", "LINK", "META", "BASE", "TEMPLATE"];
  var OPS = { "=": true, "!=": true, "に含む": true, ">=": true, "<=": true };

  function hasOwn(obj, key) { return obj != null && Object.prototype.hasOwnProperty.call(obj, key); }
  function lookup(table, key) { return hasOwn(table, key) ? table[key] : undefined; }
  function mark(name, root) { return (root || document).querySelector('[data-ipt="' + name + '"]'); }
  function setText(el, value) { if (el) el.textContent = value == null ? "" : String(value); }
  function make(tag, text, cls) {
    var el = document.createElement(tag);
    if (text != null) el.textContent = String(text);
    if (cls) el.className = cls;
    return el;
  }
  function clone(name) { return mark(name).content.firstElementChild.cloneNode(true); }
  function safeUrl(url) { return typeof url === "string" && /^https:\/\//i.test(url) ? url : null; }
  function link(text, url) {
    var href = safeUrl(url);
    var a = make(href ? "a" : "span", text);
    if (href) {
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    return a;
  }
  // 値を文字にする（文書の形の本文は、段落の中は続け、段落の間で改行する）。
  function toText(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (typeof value !== "object") return "";
    if (Array.isArray(value)) return value.map(toText).filter(Boolean).join("、");
    if (typeof lookup(value, "text") === "string") return value.text;
    if (Array.isArray(lookup(value, "content"))) {
      var inline = value.type === "paragraph" || value.type === "heading";
      return value.content.map(toText).join(inline ? "" : "\n");
    }
    var named = ["displayName", "name", "login", "value", "key"].filter(function (k) { return lookup(value, k); })[0];
    return named ? toText(value[named]) : "";
  }
  // 共通の項目にそろえる（担当・ラベルは文字の配列、ほかは文字）。remap は状態と種類の対応を当てるか。
  function normalize(row, tracker, remap) {
    var out = Object.create(null);
    if (row != null && typeof row === "object") {
      Object.keys(row).forEach(function (k) { out[k] = row[k]; });
    }
    FIELDS.forEach(function (field) {
      out[field] = hasOwn(MULTI, field) ? [].concat(out[field]).map(toText).filter(Boolean) : toText(out[field]);
    });
    if (remap && hasOwn(tracker.states, out["状態"])) out["状態"] = toText(tracker.states[out["状態"]]);
    if (remap && hasOwn(tracker.types, out["種類"])) out["種類"] = toText(tracker.types[out["種類"]]);
    out["トラッカー"] = tracker.name;
    return out;
  }

  function seconds(update) {
    var m = /^(\d+)秒$/.exec(update || "");
    return m ? Number(m[1]) : 0;
  }
  // 時刻を読む（読めない値は NaN）。日付だけの値は見る人の地方時のその日の始まり（endOfDay なら終わり）にする。
  // +0900 のようにコロンの無い時差（Jira など）は +09:00 に直して読む（Safari の Date.parse は読めないため）。
  function timeOf(value, endOfDay) {
    var days = /^(\d+)日前$/.exec(value || "");
    var day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
    var next = endOfDay ? 1 : 0;  // 終わりは次の日の始まりの直前
    if (typeof value === "number") return value;
    if (days) return Date.now() - Number(days[1]) * 86400000;
    if (day) return new Date(Number(day[1]), Number(day[2]) - 1, Number(day[3]) + next).getTime() - next;
    return typeof value === "string" ? Date.parse(value.replace(/(T[\d:.]+[+-]\d{2})(\d{2})$/, "$1:$2")) : NaN;
  }
  // 読めない時刻は、どの時刻よりも古いものとして並べる（取った後の絞り込みの >=・<= は通さない）。
  function compareTime(a, b) {
    var x = timeOf(a);
    var y = timeOf(b);
    return isNaN(x) || isNaN(y) ? isNaN(y) - isNaN(x) : x - y;
  }
  function compareText(a, b) { return toText(a).localeCompare(toText(b), "ja", { numeric: true }); }
  function two(n) { return (n < 10 ? "0" : "") + n; }
  function formatTime(value) {
    var d = new Date(timeOf(value));
    if (!value || isNaN(d.getTime())) return toText(value);
    var day = d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate());
    return day + " " + two(d.getHours()) + ":" + two(d.getMinutes());
  }
  // 取った後の絞り込み・並び・まとめ方（状態は、そのトラッカーの状態の順で比べる）。
  function statusIndex(spec, row) {
    var tracker = spec.trackers.filter(function (t) { return t.name === row["トラッカー"]; })[0] || {};
    var order = tracker.statusOrder || [];
    var i = order.indexOf(row["状態"]);
    return i < 0 ? order.length : i;
  }
  function compareField(spec, field, a, b) {
    var d = field === "状態" ? statusIndex(spec, a) - statusIndex(spec, b) : 0;
    if (d) return d;
    if (field === "更新日") return compareTime(a[field], b[field]);
    return compareText(a[field], b[field]);
  }
  function passes(row, filter) {
    var value = row[filter.field];
    var wanted = [].concat(filter.value);
    if (filter.op === "=") return wanted.indexOf(value) >= 0;
    if (filter.op === "!=") return wanted.indexOf(value) < 0;
    if (filter.op === "に含む") return [].concat(value).some(function (v) { return wanted.indexOf(v) >= 0; });
    if (filter.op === ">=") return wanted.some(function (w) { return timeOf(value) >= timeOf(w); });
    return filter.op === "<=" && wanted.some(function (w) { return timeOf(value) <= timeOf(w, true); });
  }
  function arrange(spec, rows) {
    var kept = rows.filter(function (row) {
      return (spec.filters || []).every(function (f) { return passes(row, f); });
    });
    var sort = spec.sort || [{ field: "更新日", order: "降順" }];
    return kept.sort(function (a, b) {
      for (var i = 0; i < sort.length; i += 1) {
        var d = compareField(spec, sort[i].field, a, b);
        if (d) return sort[i].order === "降順" ? -d : d;
      }
      return 0;
    });
  }
  function groupsOf(spec, rows, field) {
    var groups = [];
    var byName = new Map();
    rows.forEach(function (row) {
      var values = !field || field === "なし" ? [""] : [].concat(row[field]).filter(Boolean);
      (values.length ? values : ["なし"]).forEach(function (name) {
        if (!byName.has(name)) {
          byName.set(name, { name: name, rows: [], rep: row });
          groups.push(byName.get(name));
        }
        byName.get(name).rows.push(row);
      });
    });
    return groups.sort(function (a, b) {
      if (a.name === "なし" || b.name === "なし") return (a.name === "なし") - (b.name === "なし");
      if (hasOwn(MULTI, field)) return compareText(a.name, b.name);
      return compareField(spec, field, a.rep, b.rep);
    });
  }

  function cell(target, row, field) {
    var text = field === "更新日" ? formatTime(row[field]) : toText(row[field]);  // 担当・ラベルの配列は「、」でつなぐ
    var linked = field === "キー" || field === "URL";
    target.appendChild(linked ? link(text, row["URL"]) : make("span", text));
  }
  function fieldsInto(container, row, columns) {
    var fields = row["取れなかったもの"] ? columns.concat(["取れなかったもの"]) : columns;
    fields.forEach(function (field) {
      var node = clone("field");
      node.dataset.field = field;
      setText(mark("label", node), field);
      if (field === "取れなかったもの") setText(mark("value", node), toText(row[field]));
      else cell(mark("value", node), row, field);
      container.appendChild(node);
    });
  }

  function renderTable(spec, body, rows, columns) {
    groupsOf(spec, rows, spec.groupBy).forEach(function (group) {
      var node = clone("group");
      var name = mark("group-name", node);
      setText(name, group.name);
      name.hidden = !spec.groupBy || spec.groupBy === "なし";
      columns.forEach(function (field) {
        var th = make("th", field);
        th.scope = "col";
        mark("head", node).appendChild(th);
      });
      group.rows.forEach(function (row) {
        var tr = make("tr");
        columns.forEach(function (field) {
          var td = make("td");
          td.dataset.field = field;
          cell(td, row, field);
          tr.appendChild(td);
        });
        mark("rows", node).appendChild(tr);
      });
      body.appendChild(node);
    });
  }

  function renderKanban(spec, body, rows, columns) {
    var lanes = [];
    var seen = new Map();
    function lane(name, index) {
      if (!seen.has(name)) {
        seen.set(name, { name: name, index: index, rows: [] });
        lanes.push(seen.get(name));
      }
      seen.get(name).index = Math.min(seen.get(name).index, index);
      return seen.get(name);
    }
    spec.trackers.forEach(function (t) {
      (t.statusOrder || []).forEach(function (s, i) { lane(toText(s), i); });
    });
    rows.forEach(function (row) {
      var index = row["状態"] ? statusIndex(spec, row) : Infinity;
      lane(row["状態"] || "なし", index).rows.push(row);
    });
    lanes.sort(function (a, b) { return a.index - b.index || compareText(a.name, b.name); });
    lanes.forEach(function (l) {
      var node = clone("column");
      setText(mark("column-name", node), l.name);
      setText(mark("column-count", node), l.rows.length);
      l.rows.forEach(function (row) {
        var card = clone("card");
        fieldsInto(mark("fields", card), row, columns);
        mark("cards", node).appendChild(card);
      });
      body.appendChild(node);
    });
  }
  // 詳細の子（キー・タイトル・状態）とコメント（作者・日時・本文）の1行。
  function childItem(e) {
    var li = make("li");
    var state = lookup(e, "状態") ? "（" + toText(e["状態"]) + "）" : "";
    li.appendChild(link(toText(lookup(e, "キー")), lookup(e, "URL")));
    li.appendChild(make("span", " " + toText(lookup(e, "タイトル")) + state));
    return li;
  }
  function commentItem(e) {
    var li = make("li");
    var meta = [toText(lookup(e, "作者")), formatTime(lookup(e, "日時"))].filter(Boolean).join(" · ");
    li.appendChild(make("div", meta, "meta"));
    li.appendChild(make("div", toText(lookup(e, "本文")), "text"));
    return li;
  }
  function entriesInto(node, section, list, entries, item) {
    var target = mark(list, node);
    mark(section, node).hidden = !Array.isArray(entries);
    if (!Array.isArray(entries)) return;
    entries.forEach(function (e) { target.appendChild(item(e)); });
    if (!entries.length) target.appendChild(make("li", "無し"));
  }
  function renderDetail(spec, body, rows, columns) {
    rows.forEach(function (row) {
      var node = clone("item");
      setText(mark("item-title", node), [row["キー"], row["タイトル"]].filter(Boolean).join(" "));
      fieldsInto(mark("fields", node), row, columns);
      mark("item-body", node).hidden = !hasOwn(row, "本文");
      setText(mark("text", node), toText(row["本文"]) || "無し");
      entriesInto(node, "item-children", "children", row["子"], childItem);
      entriesInto(node, "item-comments", "comments", row["コメント"], commentItem);
      body.appendChild(node);
    });
  }

  // 一覧の行。文字か、{text, label, action}（ボタンを添える）。
  function lines(name, entries) {
    var el = mark(name);
    if (!el) return;
    el.replaceChildren.apply(el, entries.map(function (entry) {
      if (typeof entry === "string") return make("li", entry);
      var li = make("li", entry.text);
      var button = make("button", entry.label);
      button.type = "button";
      button.addEventListener("click", entry.action);
      li.appendChild(document.createTextNode(" "));
      li.appendChild(button);
      return li;
    }));
    el.hidden = !entries.length;
  }
  // 描画の段ごとに失敗を閉じ込め、どの段で失敗したかを取れなかったものに出す。
  function guard(model, label, fn, fallback) {
    try {
      return fn();
    } catch (error) {
      model.failures.push(label + " — 表示で失敗した（" + toText(error && error.message || String(error)) + "）");
      model.failed = true;
      return fallback;
    }
  }

  // 自動で取り直すトラッカーの分。view は runtime.js の snapshot（rows・truncated・loading・at・message・action・waiting・failed・
  // watching（取り直しの注記を出すか。内容を引っ込めたときは理由だけを出す）・auto（watch が生きているか））。
  function collectLive(spec, tracker, view, model) {
    if (view.rows) model.rows = model.rows.concat(view.rows);
    if (view.message && view.action) model.failures.push({ text: tracker.name + " — " + view.message, label: "承認して取る", action: view.action });
    else if (view.message) model.failures.push(tracker.name + " — " + view.message);
    if (view.failed) model.failed = true;
    if (view.at) model.times.push(view.at);
    if (view.waiting) model.waiting = true;
    if (!view.watching) return;
    var how = seconds(spec.update) ? seconds(spec.update) + "秒ごとと" : "開いたときと";
    var when = view.auto ? how + "「更新」ボタンで取り直している" : "「更新」ボタンで取り直している（自動の取り直しは登録できなかった）";
    var at = view.at ? "（最終取得 " + formatTime(view.at) + "）" : "";
    var mine = tracker.mine ? "。条件の @自分 は見る人なので、見る人によって中身が変わる" : "";
    model.notes.push(tracker.name + " は見る人の接続で、" + when + at + mine);
  }
  // 取った時点の内容のトラッカーの分。
  function collectStatic(spec, tracker, model) {
    var by = toText(spec.fetchedBy);
    var mine = tracker.mine ? "。条件の @自分 は " + by + " の担当" : "";
    model.rows = model.rows.concat((tracker.rows || []).map(function (r) { return normalize(r, tracker, false); }));
    var when = spec.fetchedAt ? " が " + formatTime(spec.fetchedAt) + " に" : " が";
    if (!isNaN(timeOf(spec.fetchedAt))) model.times.push(timeOf(spec.fetchedAt));
    model.notes.push(tracker.name + " は " + by + when + "取った内容で、自動では更新されない" + mine);
  }
  function emptyText(model) {
    if (model.failed) return "取れなかった（理由は上）";
    return model.waiting ? "取得中" : "該当するチケットは無い";
  }

  // ページを描く。views[i] は自動で取り直すトラッカーの状態（取った時点の内容なら null）。page は {stopped, refreshable}。
  function render(spec, views, page) {
    if (page.stopped) {
      blank();
      return;
    }
    var model = { rows: [], notes: [], times: [], failures: [], waiting: false, failed: false };
    (spec.failures || []).forEach(function (f) {
      model.failures.push(toText(f && f.tracker) + " — " + toText(f && f.reason));
      model.failed = true;
    });
    spec.trackers.forEach(function (tracker, index) {
      guard(model, toText(tracker.name), function () {
        var truncated = tracker.live ? views[index].truncated : tracker.truncated;
        var cut = tracker.live && views[index].loading ? "取得中（ここまでに取れた件数: " : "一覧が途中で切れている（取れた件数: ";
        if (tracker.live) collectLive(spec, tracker, views[index], model);
        else collectStatic(spec, tracker, model);
        if (typeof truncated === "number") model.failures.push(tracker.name + " — " + cut + truncated + "）");
      });
    });
    var rows = guard(model, "絞り込みと並び", function () { return arrange(spec, model.rows); }, []);
    var body = document.createDocumentFragment();
    guard(model, "本体", function () {
      var draw = { "カンバン": renderKanban, "詳細": renderDetail }[spec.kind] || renderTable;
      if (rows.length) draw(spec, body, rows, spec.columns || FIELDS);
      else body.appendChild(make("p", emptyText(model), "empty"));
    });
    guard(model, "見出し", function () {
      var oldest = model.times.length ? "最終取得 " + formatTime(Math.min.apply(null, model.times)) : "";
      setText(mark("title"), spec.title);
      setText(mark("count"), !rows.length && model.failed ? "" : rows.length + " 件");
      if (spec.title) document.title = toText(spec.title);
      setText(mark("updated"), model.waiting ? "取得中" : oldest);
      mark("refresh").hidden = !page.refreshable;
    });
    lines("failures", model.failures);
    lines("notes", model.notes);
    mark("body").replaceChildren(body);
  }
  // 見る人が変わったとき: 何も出さない。
  function blank() {
    ["title", "count", "updated"].forEach(function (name) { setText(mark(name), ""); });
    mark("refresh").hidden = true;
    lines("failures", []);
    lines("notes", []);
    mark("body").replaceChildren();
  }

  function nodes(root, selector) { return Array.prototype.slice.call(root.querySelectorAll(selector)); }
  // 印を付けた要素の確かめ（ページと雛形の中）。雛形の中の <template>（入れ子）も誤りにする。
  function markProblems() {
    var found = [];
    var roots = [document].concat(nodes(document, "template").map(function (t) { return t.content; }));
    roots.forEach(function (root, i) {
      if (i > 0 && nodes(root, "template").length) found.push("テンプレートの雛形の中に <template> がある（入れ子にしない）");
      nodes(root, "[data-ipt]").forEach(function (el) {
        var name = el.getAttribute("data-ipt");
        var prototype = i === 0 && el.tagName === "TEMPLATE" && PROTOTYPES.indexOf(name) >= 0;
        if (el.namespaceURI === HTML_NS && (UNMARKABLE.indexOf(el.tagName) < 0 || prototype)) return;
        found.push("テンプレートの印 " + name + " を付けてはいけない要素 <" + el.localName + "> に付けている");
      });
    });
    return found;
  }
  // 描く前の確かめ: 型・テンプレートの印と雛形・印を付けた要素・絞り込みの比べ方・trackers の形。
  function problems(spec) {
    var found = markProblems();
    var kindMarks = hasOwn(KINDS, spec.kind) ? KINDS[spec.kind] : null;
    var prototypes = nodes(document, "template[data-ipt]").filter(function (t) { return PROTOTYPES.indexOf(t.getAttribute("data-ipt")) >= 0; });
    if (!kindMarks) found.push("型が分からない: " + toText(spec.kind));
    COMMON_MARKS.forEach(function (name) {
      if (!mark(name)) found.push("テンプレートに印 " + name + " が無い");
    });
    (kindMarks || []).forEach(function (name) {
      var el = mark(name);
      var inside = prototypes.some(function (t) { return mark(name, t.content); });
      if (PROTOTYPES.indexOf(name) < 0 && !inside) found.push("テンプレートの雛形の中に印 " + name + " が無い");
      if (PROTOTYPES.indexOf(name) < 0) return;
      if (!el || el.tagName !== "TEMPLATE" || !el.content.firstElementChild) found.push("テンプレートの雛形 " + name + " が <template> に無い");
    });
    (spec.filters || []).forEach(function (f) {
      if (!hasOwn(OPS, f && f.op)) found.push("取った後の絞り込みの比べ方が分からない: " + toText(f && f.op));
    });
    if (!Array.isArray(spec.trackers)) found.push("trackers が無い");
    else if (!spec.trackers.every(function (t) { return t != null && typeof t === "object" && !Array.isArray(t); })) found.push("trackers の要素がオブジェクトでない");
    return found;
  }

  window.iptView = {
    fields: FIELDS.slice(),
    toText: toText,
    normalize: normalize,
    seconds: seconds,
    problems: problems,
    render: render,
    showProblems: function (found) { lines("failures", found); },
    onRefresh: function (handler) { mark("refresh").addEventListener("click", handler); }
  };
})();
