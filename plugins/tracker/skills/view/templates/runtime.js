/*
 * tracker:view のページの取り直し・誤りの扱い・状態。テンプレートから render.js の後に読み込まれ、描画は window.iptView に任せる。
 * 自動で取り直すトラッカーは mcp 機能の watchTool で取り直し、「更新」ボタンで invalidate する。
 * 続きのページは最後まで、型が 詳細 の1件ずつの呼び出し（each）はページ全体で同時に EACH_LIMIT 件までを callTool で取る。
 * 取り直しの途中で新しい知らせが来ても止めず、終わってから一番新しいものを取る（見る人の「更新」だけは止める）。
 * トラッカーの状態は phase の1つの名前で表す:
 *   idle 取っていない | running 取得中 | replayed 再生を仕上がっていない内容として出し、新しい結果を待つ | done 取れた
 *   failed 一時的な誤り（前の内容を残す） | awaiting 承認待ち（内容を引っ込め、ボタンを出す） | approving 承認して取っている
 *   held 承認が要るトラッカーの新しい結果に続きのページか each が要る（前の内容を残し、ボタンを出す）
 *   denied 拒否された（内容を引っ込める） | offline この表示では mcp が使えない | stopped 見る人が変わり止めた
 * phase と別に持つもの: content（誤りのときも残す、前に出した内容）、approval（一度 approval_required になった印）、
 * pending（取り直しの途中に来た一番新しい知らせ）、cache（each の結果。キーと更新日ごと）。
 */
(function () {
  "use strict";

  var view = window.iptView;
  // 許可の拒否と、この表示でコネクタを使えない誤り。そのトラッカーの内容をまるごと引っ込め、承認の印も消す。
  var DENIALS = ["needs_reauth", "server_not_connected", "server_not_found", "selection_required", "blocked_by_policy",
    "consent_required", "not_in_manifest", "not_granted", "capability_disabled", "capability_removed"];
  var OFFLINE = ["not_granted", "capability_disabled", "capability_removed"];  // この表示では mcp が使えず、取り直していない
  // watch の登録の誤り（古いシェル・上限・重なり。mcp.d.ts）。この誤りと OFFLINE の後は、その watch から何も来ない。
  var UNREGISTERED = ["bad_request", "transform_error"].concat(OFFLINE);
  var RETRACTS = ["deny", "approve"];  // 内容を引っ込める分け方（watch の approval_required も mcp の決まりで引っ込める）
  var FAILED = ["awaiting", "denied", "offline", "failed"];  // 取れなかったトラッカーとして出す phase
  // 内容を引っ込めたか止めた phase。最後に受け取った結果から取り直さず、取り直しの注記も出さない（理由だけを出す）。
  var RETRACTED = ["denied", "awaiting", "offline", "stopped"];
  var BUTTONS = ["awaiting", "held"];  // 「承認して取る」を出す phase
  var EACH_LIMIT = 4;
  var STALE = { stale: true };  // 世代が変わり、捨てる結果の印

  var spec = null;
  var mcp = null;
  var stopped = false;
  var states = [];
  var watches = new Map();
  var queue = [];
  var running = 0;

  function hasOwn(obj, key) { return obj != null && Object.prototype.hasOwnProperty.call(obj, key); }
  function dict() { return Object.create(null); }
  // "__proto__" などのキーでもプロトタイプを変えずに、自分のプロパティとして置く。
  function put(obj, key, value) {
    Object.defineProperty(obj, key, { value: value, enumerable: true, writable: true, configurable: true });
    return obj;
  }
  function plain(value) { return value != null && typeof value === "object" && !Array.isArray(value); }
  // 結果の中の場所 "a.b[].c"。[] の付いた所は配列の要素ごとに進む。継いだプロパティは読まない。
  function pick(obj, path) {
    if (path == null || path === "") return obj;
    var current = [obj];
    var many = false;
    String(path).split(".").forEach(function (part) {
      var each = /\[\]$/.test(part);
      var name = each ? part.slice(0, -2) : part;
      if (each) many = true;
      current = current.reduce(function (next, item) {
        var value = name === "" ? item : hasOwn(item, name) ? item[name] : undefined;
        return next.concat(each && Array.isArray(value) ? value : [value]);
      }, []);
    });
    return many ? current.filter(function (v) { return v != null; }) : current[0];
  }
  function isTemplate(rule) { return plain(rule) && typeof rule.template === "string"; }
  function valueAt(item, rule) {
    if (!isTemplate(rule)) return pick(item, rule);
    return rule.template.replace(/\{([^{}]+)\}/g, function (_, path) { return view.toText(pick(item, path)); });
  }
  // 入力の中の "{<共通の項目>}" を、その行の値に置き換える。callTool に渡すので普通のオブジェクトで返す。
  function fill(input, row) {
    if (typeof input === "string") {
      return input.replace(/\{([^{}]+)\}/g, function (all, field) { return hasOwn(row, field) ? view.toText(row[field]) : all; });
    }
    if (Array.isArray(input)) return input.map(function (v) { return fill(v, row); });
    if (!plain(input)) return input;
    return Object.keys(input).reduce(function (out, k) { return put(out, k, fill(input[k], row)); }, {});
  }
  function inputOf(tracker) {
    var input = tracker.live.list.input;
    return input == null ? {} : input;
  }
  function toRow(item, tracker) {
    var rules = tracker.live.fields || {};
    var row = dict();
    view.fields.forEach(function (field) {
      if (hasOwn(rules, field)) row[field] = valueAt(item, rules[field]);
    });
    return view.normalize(row, tracker, true);
  }
  function items(list, payload) {
    var value = list.items ? pick(payload, list.items) : payload;
    return value == null ? [] : [].concat(value);
  }
  function cursorOf(list, page) {
    var next = list.next;
    var cursor = next ? pick(page, next.cursor) : null;
    if (!next || cursor == null || cursor === "") return null;
    return next.last && pick(page, next.last) === true ? null : cursor;
  }
  // 1ページ目のほかに callTool で取るものがあるか: 続きのページか、手元に残した結果の無い（更新日が変わった）行の each。
  function needsMore(index, payload) {
    var tracker = spec.trackers[index];
    if (cursorOf(tracker.live.list, payload) != null) return true;
    return items(tracker.live.list, payload).some(function (item) {
      var row = toRow(item, tracker);
      return (tracker.live.each || []).some(function (rule, r) { return !states[index].cache.has(cacheKey(r, row)); });
    });
  }

  // 誤りの code ごとの理由（直し方がある code は、その直し方を出す）。code の無いものはページの中の失敗。
  function reason(error, server) {
    var code = error && error.code;
    var name = "「" + (server || "コネクタ") + "」";
    if (typeof code !== "string") return "取った結果を出せなかった（" + view.toText(error && error.message || String(error)) + "）";
    switch (code) {
      case "needs_reauth": return "claude.ai の設定のコネクタで " + name + " をつなぎ直すと取れる";
      case "server_not_connected": case "server_not_found": return "claude.ai の設定のコネクタに " + name + " を追加すると取れる";
      case "selection_required": return "同じ名前の " + name + " が複数あり、どれを使うか選ばれていない";
      case "not_in_manifest": case "consent_required": return "このページで " + name + " を使うことが許されていない";
      case "approval_required": return name + " で取るには見る人の承認が要る";
      case "blocked_by_policy": return "組織の設定で " + name + " が使えない";
      case "server_unavailable": case "rate_limited": return name + " に一時的につながらない";
      case "tool_error": return "ツールが失敗を返した: " + view.toText(error.message);
      case "not_granted": case "capability_disabled": case "capability_removed": return "この表示ではコネクタで取り直せない";
      default: return "取れなかった（" + code + "）";
    }
  }
  // retryAfterMs（60秒まで）の後に、少しずらして待つ。
  function retryDelay(error) {
    var after = typeof error.retryAfterMs === "number" ? Math.min(Math.max(error.retryAfterMs, 0), 60000) : 0;
    return after + 500 + Math.floor(Math.random() * 1500);
  }
  // 誤りの code の分け方。watch・続きのページ・each・承認して取るの、どの経路の誤りもここで分ける。
  // stop: ページ全体で何も出さず以降は呼ばない | approve: 引っ込めてボタンを出す | deny: 引っ込める | keep: 前の内容を残す（知らない code を含む）
  function kindOf(error) {
    var code = error && error.code;
    if (code === "user_changed") return "stop";
    if (code === "approval_required") return "approve";
    if (DENIALS.indexOf(code) >= 0) return "deny";
    return "keep";
  }

  // ms だけ待つ（待った後に呼ぶ側が世代を確かめ、古い世代なら呼ばずに終える）。
  function pause(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }
  // トラッカーの新しい世代を始める。古い世代の呼び出しと待ちは止め（AbortSignal）、結果は捨てる。
  function begin(state) {
    if (state.ctrl) state.ctrl.abort();
    state.ctrl = typeof AbortController === "function" ? new AbortController() : null;
    state.gen += 1;
    return { state: state, gen: state.gen, retries: 1, signal: state.ctrl ? state.ctrl.signal : undefined };
  }
  function alive(ctx) { if (ctx.gen !== ctx.state.gen || !mcp || stopped) throw STALE; }
  function direct(task) { return Promise.resolve().then(task); }
  // 1件ずつの呼び出しの順番待ち（ページ全体で同時に EACH_LIMIT 件まで）。
  function limited(task) {
    return new Promise(function (resolve, reject) {
      queue.push({ task: task, resolve: resolve, reject: reject });
      pump();
    });
  }
  function pump() {
    while (running < EACH_LIMIT && queue.length) {
      var job = queue.shift();
      running += 1;
      Promise.resolve().then(job.task).then(job.resolve, job.reject).then(release);
    }
  }
  function release() {
    running -= 1;
    pump();
  }
  // 読むだけの呼び出し。slot は同時の数の枠（each は limited）。retryable が真の誤りは、取り直し1回（ctx）につき1回だけ、
  // 枠を返して少し待ち（新しい世代で止まる）、世代を確かめてから呼び直す。
  function call(ctx, server, tool, input, slot) {
    function once() {
      return slot(function () {
        alive(ctx);
        return mcp.callTool(server, tool, input, ctx.signal ? { signal: ctx.signal } : undefined);
      });
    }
    return once().then(null, function (error) {
      alive(ctx);
      if (!error || error.retryable !== true || ctx.retries < 1) throw error;
      ctx.retries -= 1;
      return pause(retryDelay(error)).then(function () {
        alive(ctx);
        return once();
      });
    });
  }
  // 受け取った結果と、その時刻（cache があれば storedAt、無ければ受け取った時刻）。
  function receive(result) {
    var cache = result && plain(result.cache) ? result.cache : null;
    return { result: result, at: cache && typeof cache.storedAt === "number" ? cache.storedAt : Date.now() };
  }
  // 出す内容: rows・truncated（切れたときの件数）・at（1ページ目の時刻）・loading（取得中で、truncated はここまでの件数）。
  function show(state, content) {
    state.rows = content ? content.rows : null;
    state.truncated = content ? content.truncated : null;
    state.at = content ? content.at : null;
    state.loading = !!(content && content.loading);
  }

  // each の結果はキーと更新日で手元に残す（更新日の無い行は変わったか分からないので残さない）。
  function cacheKey(r, row) {
    if (!row["キー"] || !row["更新日"]) return null;
    return JSON.stringify([r, row["キー"], row["更新日"]]);
  }
  function assign(row, values) {
    Object.keys(values).forEach(function (field) { row[field] = values[field]; });
  }
  // 手元に残した each の結果を行に当てる（行を作るとき・each の前）。当てたら true。
  function applyCached(job, row, r) {
    var key = cacheKey(r, row);
    if (!key || !job.state.cache.has(key)) return false;
    job.used.set(key, job.state.cache.get(key));
    assign(row, job.state.cache.get(key));
    return true;
  }
  function rowsOf(job, got) {
    return got.map(function (item) {
      var row = toRow(item, job.tracker);
      (job.tracker.live.each || []).forEach(function (rule, r) { applyCached(job, row, r); });
      return row;
    });
  }
  // 届いた行をすぐ出す。前の内容の件数と時刻は混ぜず、この取り直しの途中（取得中、ここまでの件数）として出す。
  function addRows(job, got) {
    job.rows = job.rows.concat(rowsOf(job, got));
    show(job.state, { rows: job.rows, truncated: job.rows.length, at: job.at, loading: true });
    paint();
  }
  function newJob(index, manual) {
    var state = states[index];
    var ctx = begin(state);
    return { index: index, state: state, tracker: spec.trackers[index], ctx: ctx, manual: manual, rows: [], used: new Map(),
      at: null, page: null, seen: [], first: false, listed: false, cut: null };
  }

  // 1つの取り直し: 1ページ目（received が無ければ callTool で取る）から、続きのページ（最後まで）と each を callTool で取る。
  // 行は届いた分からすぐ出す。manual は見る人の「承認して取る」から始まったもの。終わったら、待っている一番新しい知らせを取る。
  function run(index, received, manual) {
    var job = newJob(index, manual);
    var live = job.tracker.live;
    job.state.phase = manual ? "approving" : "running";
    job.state.error = null;
    paint();
    var first = received ? Promise.resolve(received) : call(job.ctx, live.server, live.list.tool, inputOf(job.tracker), direct).then(receive);
    first.then(function (got) {
      alive(job.ctx);
      job.at = got.at;
      job.page = got.result && got.result.payload;
      addRows(job, items(live.list, job.page));
      job.first = true;
      return nextPages(job);
    }).then(function (cut) {
      alive(job.ctx);
      job.listed = true;
      job.cut = cut;
      return extras(job);
    }).then(function () {
      safely(index, function () { finish(job); }, partialOf(job));
    }, function (error) {
      if (job.ctx.gen === job.state.gen) settle(index, error, partialOf(job));
    }).then(function () {
      if (job.state.phase !== "running" && job.state.phase !== "approving") next(index);  // 新しい取り直しが始まっていなければ
    });
  }
  function nextPages(job) {
    var list = job.tracker.live.list;
    var cursor = cursorOf(list, job.page);
    var key = JSON.stringify(cursor);
    if (cursor == null) return null;
    if (job.seen.indexOf(key) >= 0) return "続きのページの印が前と同じで、先へ進めない";
    job.seen.push(key);
    var input = put(fill(inputOf(job.tracker), dict()), list.next.param, cursor);
    return call(job.ctx, job.tracker.live.server, list.tool, input, direct).then(function (result) {
      alive(job.ctx);
      job.page = result && result.payload;
      var got = items(list, job.page);
      if (!got.length) return cursorOf(list, job.page) == null ? null : "続きのページが空で、先へ進めない";
      addRows(job, got);
      return nextPages(job);
    });
  }
  // 型が 詳細 のときの本文・子・コメント（each の決まり）。手元に残した結果は当て、残りを順番待ちで取り、届いた分から入れる。
  function extras(job) {
    var calls = [];
    job.rows.forEach(function (row) {
      (job.tracker.live.each || []).forEach(function (rule, r) {
        if (!applyCached(job, row, r)) calls.push(fetchExtra(job, row, rule, r));
      });
    });
    return Promise.all(calls);
  }
  function fetchExtra(job, row, rule, r) {
    var server = job.tracker.live.server;
    return call(job.ctx, server, rule.tool, fill(rule.input, row), limited).then(function (result) {
      alive(job.ctx);
      var values = extract(rule.set || {}, result && result.payload);
      var key = cacheKey(r, row);
      if (key) job.used.set(key, values);
      assign(row, values);
      paint();
    }, function (error) {
      alive(job.ctx);
      if (kindOf(error) !== "keep") throw error;  // 止める・引っ込める・承認は、トラッカーごとに fail で当てる
      row["取れなかったもの"] = [].concat(row["取れなかったもの"] || [], reason(error, server));
      paint();
    });
  }
  function extract(set, payload) {
    var values = dict();
    Object.keys(set).forEach(function (field) {
      var how = set[field];
      if (!plain(how) || isTemplate(how)) {
        values[field] = view.toText(valueAt(payload, how));
        return;
      }
      values[field] = items(how, payload).map(function (item) { return entryOf(how.fields || {}, item); });
    });
    return values;
  }
  function entryOf(fields, item) {
    var out = dict();
    Object.keys(fields).forEach(function (k) { out[k] = view.toText(valueAt(item, fields[k])); });
    return out;
  }
  function finish(job) {
    var state = job.state;
    alive(job.ctx);
    state.content = { rows: job.rows, truncated: job.cut ? job.rows.length : null, at: job.at, loading: false };
    state.cache = job.used;
    state.error = job.cut;
    state.phase = "done";
    if (job.manual) state.pending = null;  // 承認して取れた: その間に来た watch の知らせは古い
    show(state, state.content);
    paint();
  }
  // その取り直しで出していた行（前の内容が無いときに出す）。
  function partialOf(job) {
    if (!job.first) return null;
    return { rows: job.rows, truncated: !job.listed || job.cut ? job.rows.length : null, at: job.at };
  }

  // トラッカー1つの処理を行い、例外は settle に回す。知らせ・続き・承認・更新のどの経路もここを通し、running のまま残さない。
  function safely(index, task, partial) {
    try {
      task();
    } catch (error) {
      settle(index, error, partial);
    }
  }
  function dispatch(index, message) { safely(index, function () { onEvent(index, message); }); }
  // 誤りを当てる。fail 自身が失敗しても、取り直しを止めて一時的な誤りとして置く（前の内容は残す）。
  function settle(index, error, partial) {
    if (error === STALE) return;
    try {
      fail(index, error, partial);
    } catch (again) {
      begin(states[index]);
      states[index].phase = "failed";
      states[index].error = reason(again);
    }
  }
  // 誤りを kindOf で分けて当てる（どの経路でも同じ）。
  function fail(index, error, partial) {
    var state = states[index];
    var kind = kindOf(error);
    if (kind === "stop") {
      stop();
      return;
    }
    begin(state);  // 取っている途中の呼び出しは止める
    state.error = reason(error, spec.trackers[index].live.server);
    if (RETRACTS.indexOf(kind) >= 0) retract(state, kind, error.code);
    else keep(state, partial);
    paint();
  }
  function retract(state, kind, code) {
    state.content = null;
    state.cache = new Map();
    state.approval = kind === "approve";  // 承認の印は、拒否で消す
    show(state, null);
    if (kind === "approve") {
      state.phase = "awaiting";  // 承認して取る間に来た知らせ（pending）は、この後に取る
      return;
    }
    state.pending = null;
    state.phase = OFFLINE.indexOf(code) >= 0 ? "offline" : "denied";
  }
  function keep(state, partial) {
    show(state, state.content || partial);
    state.phase = "failed";
    if (state.content) state.error += "（前に取った内容を出している）";
  }

  // watch の知らせ（message は {error} か {received, refetch}）。取り直しの途中なら一番新しいものだけを pending に置く。
  function onEvent(index, message) {
    var state = states[index];
    var kind = message.error ? kindOf(message.error) : null;
    if (stopped) return;
    if (kind === "stop" || kind === "deny") fail(index, message.error);
    else if (state.phase === "running" || state.phase === "approving") state.pending = message;
    else if (!message.error) onData(index, message);
    else if (kind !== "keep" || BUTTONS.indexOf(state.phase) < 0) fail(index, message.error);  // 承認待ちの間の一時的な誤りは、ボタンを待つ
  }
  function onData(index, message) {
    var state = states[index];
    var result = message.received.result || {};
    var more = needsMore(index, result.payload);
    if (more && state.approval) hold(state);
    else if (more && !message.refetch && plain(result.cache) && result.cache.revalidating === true) replay(index, message.received);
    else run(index, message.received, false);
  }
  // 承認が要るトラッカーの新しい結果に、続きのページか each が要る: 自分では呼ばず、前の内容を残してボタンを待つ。
  function hold(state) {
    if (state.phase === "awaiting") return;
    state.phase = "held";
    state.error = "新しい結果の続きのページ・1件ずつを取るには見る人の承認が要る";
    show(state, state.content);
    paint();
  }
  // 取り直しが既に走っている再生: 1ページ目の行を仕上がっていない内容として出し（切れたことと件数）、新しい結果を待つ。
  function replay(index, received) {
    var job = newJob(index, false);
    var live = job.tracker.live;
    var payload = received.result.payload;
    var rows = rowsOf(job, items(live.list, payload));
    job.state.content = { rows: rows, truncated: cursorOf(live.list, payload) != null ? rows.length : null, at: received.at };
    job.state.phase = "replayed";
    job.state.error = null;
    show(job.state, job.state.content);
    paint();
  }
  function next(index) {
    var pending = states[index].pending;
    if (!pending) return;
    states[index].pending = null;
    dispatch(index, pending);
  }
  // 「承認して取る」: 見る人の操作から、一覧・続きのページ・each をまとめて callTool で取る（承認はこの間にだけ求められる。watch は残す）。
  function approve(index) {
    if (!mcp || stopped || states[index].phase === "approving") return;
    safely(index, function () { run(index, null, true); });
  }
  // 見る人が変わった（user_changed）: ページ全体で何も出さず、途中の結果も捨て、以降は呼ばない。
  function stop() {
    stopped = true;
    mcp = null;
    queue.splice(0).forEach(function (job) { job.reject(STALE); });
    watches.forEach(function (w) {
      clearTimeout(w.timer);
      if (w.unsub) w.unsub();
    });
    states.forEach(function (state) {
      begin(state);
      retract(state, "deny");  // 内容・途中の知らせ・手元の結果を捨てる
      state.phase = "stopped";
    });
    paint();
  }

  // 同じ server・tool・input（キーの順は問わない）の watch は1つにまとめる（同じ watch を2回登録すると bad_request になる）。
  function identity(value) {
    if (Array.isArray(value)) return "[" + value.map(identity).join(",") + "]";
    if (!plain(value)) return JSON.stringify(value === undefined ? null : value);
    return "{" + Object.keys(value).sort().map(function (k) { return JSON.stringify(k) + ":" + identity(value[k]); }).join(",") + "}";
  }
  function watch(index, options) {
    var live = spec.trackers[index].live;
    var input = inputOf(spec.trackers[index]);
    var key = identity([live.server, live.list.tool, input]);
    var w = watches.get(key);
    if (!w) {
      w = { server: live.server, tool: live.list.tool, input: input, indices: [], unsub: null, retried: false, timer: null, last: null,
        alive: true };
      watches.set(key, w);
      try {
        w.unsub = mcp.watchTool(w.server, w.tool, w.input, function (ev) { deliver(w, ev); }, options);
      } catch (error) {
        w.alive = false;  // 登録で投げた: 知らせは来ないので、まとめたトラッカーがそろってから誤りとして渡す
        Promise.resolve().then(function () { deliver(w, { type: "error", error: error }); });
      }
    }
    w.indices.push(index);
    states[index].watch = w;
  }
  // watch の知らせ。引っ込める誤りの後は前の結果（last）を捨て、登録の誤りの後は watch が生きていない印を付ける。
  function deliver(w, ev) {
    var error = ev && ev.type === "error" ? ev.error || {} : null;
    var message = error ? { error: error } : { received: receive(ev && ev.result) };
    if (error) {
      if (kindOf(error) !== "keep") w.last = null;
      if (UNREGISTERED.indexOf(error.code) >= 0) w.alive = false;
      retry(w, error);
    } else {
      w.last = message.received;
      rearm(w);
    }
    w.indices.forEach(function (i) { dispatch(i, message); });
  }
  // invalidate の断りは watch の誤りの知らせと同じに分ける。残す断りなら、見る人の「更新」（fallback）のときだけ最後の結果から取り直す。
  // capability_removed は、ここでは invalidate の無い古い基盤の断りなので残す断りとする（mcp.d.ts: 断りは何も消えなかったとして続ける）。
  function invalidate(w, fallback) {
    if (!mcp || stopped) return;
    Promise.resolve().then(function () { return mcp.invalidate(w.server, w.tool, w.input); }).then(null, function (error) {
      var kind = error && error.code === "capability_removed" ? "keep" : kindOf(error);
      if (stopped) return;
      if (kind !== "keep") deliver(w, { type: "error", error: error });
      else if (fallback && w.last) w.indices.forEach(function (i) {
        if (RETRACTED.indexOf(states[i].phase) < 0) dispatch(i, { received: w.last, refetch: true });
      });
    });
  }
  // 取れたか見る人が更新した: 待っている取り直しを取り消し、一時的な誤りをまた1回取り直してよいことにする。
  function rearm(w) {
    clearTimeout(w.timer);
    w.timer = null;
    w.retried = false;
  }
  // watch の retryable な誤り: 取れるか見る人が更新するまでに1回だけ、少し待って invalidate する（まとめた watch でも1回）。
  // 「少し待って取り直す」は待っている間だけ出す（断られても最後の結果からは取り直さない。誤りの出た1ページ目は取り直せないため）。
  function retry(w, error) {
    if (error.retryable !== true || kindOf(error) !== "keep" || w.retried) return;
    w.retried = true;
    w.timer = setTimeout(function () {
      w.timer = null;
      invalidate(w, false);
      paint();
    }, retryDelay(error));
  }
  // 見る人の「更新」: 取り直しの途中なら止め（承認して取る途中は除く）、生きている watch は invalidate し、
  // 生きていない watch のトラッカーは callTool から取り直す（内容を引っ込めたものと承認して取る途中のものは除く）。
  function refresh() {
    if (!mcp || stopped) return;
    states.forEach(function (state) {
      if (state.phase !== "running") return;
      begin(state);
      state.pending = null;
      state.phase = "idle";
      show(state, state.content);
    });
    watches.forEach(function (w) {
      rearm(w);
      if (w.alive) invalidate(w, true);
      else w.indices.forEach(function (i) {
        if (states[i].phase !== "offline" && states[i].phase !== "approving") safely(i, function () { run(i, null, false); });
      });
    });
    paint();
  }
  function connect() {
    var claude = window.claude;  // 保存したファイルなど、ビューアの外では window.claude が無い
    var usable = claude && typeof claude.use === "function";
    var use = usable ? Promise.resolve().then(function () { return claude.use("mcp"); }) : Promise.resolve(null);
    use.then(null, function () { return null; }).then(function (namespace) {
      if (stopped) return;
      mcp = namespace || null;
      var options = view.seconds(spec.update) ? { refetchInterval: view.seconds(spec.update) * 1000 } : {};  // 開いたとき: 間隔なし
      spec.trackers.forEach(function (tracker, index) {
        if (!tracker.live) return;
        if (mcp) safely(index, function () { watch(index, options); });
        else fail(index, { code: "not_granted" });  // この表示では mcp が使えない
      });
      paint();
    });
  }

  // render.js に渡すトラッカーの状態。
  function snapshot(state, index) {
    var failed = FAILED.indexOf(state.phase) >= 0 || state.phase === "held" && !state.rows;
    var button = !!mcp && BUTTONS.indexOf(state.phase) >= 0;
    var retrying = state.phase === "failed" && !!state.watch && state.watch.timer != null;
    return {
      rows: state.rows,
      truncated: state.truncated,
      loading: state.loading,
      at: state.at,
      message: state.phase === "approving" ? "承認を待っている" : state.error && state.error + (retrying ? "。少し待って取り直す" : ""),
      action: button ? function () { approve(index); } : null,
      waiting: !state.at && !failed,
      failed: failed,
      watching: !!mcp && RETRACTED.indexOf(state.phase) < 0,
      auto: !!state.watch && state.watch.alive
    };
  }
  function paint() {
    var views = spec.trackers.map(function (tracker, index) { return tracker.live ? snapshot(states[index], index) : null; });
    var refreshable = !!mcp && spec.trackers.some(function (t) { return t.live; });
    view.render(spec, views, { stopped: stopped, refreshable: refreshable });
  }

  // live の形（server・list.tool・list.input・next.param・each の tool）。
  function liveProblems() {
    var found = [];
    spec.trackers.forEach(function (t) {
      var live = t.live;
      if (live && spec.update === "しない") found.push("更新が しない なのに live がある: " + view.toText(t.name));
      else if (live && !liveShaped(live)) found.push("live の形が分からない: " + view.toText(t.name));
    });
    return found;
  }
  function liveShaped(live) {
    function str(v) { return typeof v === "string" && v !== ""; }
    var list = live.list;
    if (!plain(live) || !str(live.server) || !plain(list) || !str(list.tool)) return false;
    if (list.input != null && !plain(list.input)) return false;
    if (list.next && !str(list.next.param)) return false;
    return live.each == null || Array.isArray(live.each) && live.each.every(function (r) { return r && str(r.tool); });
  }
  function readSpec() {
    try {
      var parsed = JSON.parse(document.getElementById("ip-tracker-view").textContent);
      return plain(parsed) ? parsed : null;
    } catch (e) {
      return null;
    }
  }

  function start() {
    spec = readSpec();
    var found = spec ? view.problems(spec) : ["ページのデータ（印の JSON）が読めない"];
    if (!found.length) found = liveProblems();
    if (found.length) {
      view.showProblems(found);
      return;
    }
    states = spec.trackers.map(function () {
      return { phase: "idle", rows: null, truncated: null, at: null, content: null, error: null, approval: false, pending: null,
        cache: new Map(), gen: 0, ctrl: null, loading: false, watch: null };
    });
    // ボタンと watch を最初の描画より前に登録する（描画で失敗しても取り直しは動く）。
    view.onRefresh(refresh);
    if (spec.trackers.some(function (t) { return t.live; })) connect();
    paint();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
