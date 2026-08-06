(function () {
  "use strict";

  var SCRIPT_CLOSE = "</scr" + "ipt>";
  var EDITOR_SITE_ORIGIN = "https://tournament-timetable.surge.sh";
  var PUBLISHED_JSON_PATH = "published/timetable.json";
  var VIEWER_DEPLOY_REDIRECTS = "/    /index.html    200\n/view.html    /index.html    200\n";
  var VIEWER_DEPLOY_VIEW_HTML = [
    "<!DOCTYPE html>",
    '<html lang="ja">',
    "<head>",
    '  <meta charset="UTF-8" />',
    '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
    "  <title>\u30c8\u30fc\u30ca\u30e1\u30f3\u30c8 \u30bf\u30a4\u30e0\u30c6\u30fc\u30d6\u30eb\uff08\u95b2\u89a7\uff09</title>",
    "  <scr" + "ipt>",
    "    (function () {",
    "      const params = new URLSearchParams(location.search);",
    '      params.set("mode", "view");',
    '      location.replace("/?" + params.toString());',
    "    })();",
    "  </scr" + "ipt>",
    "</" + "head>",
    "<body>",
    "  <p>\u8aad\u307f\u8fbc\u307f\u4e2d...</p>",
    "</" + "body>",
    "</" + "html>",
    ""
  ].join("\n");
  var VIEWER_DEPLOY_NETLIFY_TOML = "[build]\n  publish = \".\"\n  command = \"echo 'Static site - no build step'\"\n\n[[headers]]\n  for = \"/published/*\"\n  [headers.values]\n    Cache-Control = \"no-cache, no-store, must-revalidate\"\n\n[[headers]]\n  for = \"/index.html\"\n  [headers.values]\n    Cache-Control = \"no-cache, no-store, must-revalidate\"\n\n[[headers]]\n  for = \"/view.html\"\n  [headers.values]\n    Cache-Control = \"no-cache, no-store, must-revalidate\"\n";
  var VIEWER_DEPLOY_FALLBACKS = {
    "view.html": VIEWER_DEPLOY_VIEW_HTML,
    "netlify.toml": VIEWER_DEPLOY_NETLIFY_TOML,
    "_redirects": VIEWER_DEPLOY_REDIRECTS
  };

  function splitViewerHtmlAtHead(html) {
    var source = String(html || "");
    var match = source.match(/<\/head>/i);
    if (!match || match.index < 0) {
      return { head: source, afterHead: "" };
    }
    return {
      head: source.slice(0, match.index),
      afterHead: source.slice(match.index + match[0].length)
    };
  }

  function getViewerHtmlAfterHead(html) {
    return splitViewerHtmlAtHead(html).afterHead;
  }

  function getViewerBodyCloseIndex(html) {
    return String(html || "").toLowerCase().lastIndexOf("</body>");
  }

  function getViewerMainScriptOpenMatch(html) {
    var afterHead = getViewerHtmlAfterHead(html);
    var match = afterHead.match(/<script>\s*\n\s*const APP_MODE/);
    if (!match) return null;
    return {
      index: String(html).length - afterHead.length + match.index,
      0: match[0]
    };
  }

  function getViewerMainScriptCloseEnd(html) {
    var openMatch = getViewerMainScriptOpenMatch(html);
    if (!openMatch) return -1;
    var bodyClose = getViewerBodyCloseIndex(html);
    var regionEnd = bodyClose >= 0 ? bodyClose : String(html || "").length;
    var region = String(html || "").slice(openMatch.index, regionEnd);
    var relativeClose = region.lastIndexOf(SCRIPT_CLOSE);
    if (relativeClose < 0) return -1;
    return openMatch.index + relativeClose + SCRIPT_CLOSE.length;
  }

  function getViewerHtmlTailAfterMainScript(html) {
    var afterMainScript = getViewerMainScriptCloseEnd(html);
    if (afterMainScript < 0) return String(html || "");
    var bodyClose = getViewerBodyCloseIndex(html);
    var tailEnd = bodyClose >= 0 ? bodyClose : String(html || "").length;
    return String(html || "").slice(afterMainScript, tailEnd).trim();
  }

  function getViewerBodyTag(html) {
    var afterHead = getViewerHtmlAfterHead(html);
    if (!afterHead) return "";
    var beforeScript = afterHead.split(/<script\b/i)[0];
    var match = beforeScript.match(/<body\b[^>]*>/i);
    return match ? match[0] : "";
  }

  function buildViewerModeBodyTag(bodyTag) {
    if (!bodyTag || /\bviewer-mode\b/.test(bodyTag)) return bodyTag;
    if (/^<body\s*>$/i.test(bodyTag)) return '<body class="viewer-mode">';
    if (/class=/i.test(bodyTag)) {
      return bodyTag.replace(
        /class=(["'])([^"']*)\1/i,
        function (_all, quote, value) {
          return "class=" + quote + value + " viewer-mode" + quote;
        }
      );
    }
    return bodyTag.replace(/<body(\s[^>]*)>/i, '<body$1 class="viewer-mode">');
  }

  function ensureViewerModeBodyClass(html) {
    var source = String(html || "");
    var split = splitViewerHtmlAtHead(source);
    var head = split.head;
    var afterHead = split.afterHead;
    if (!afterHead) return source;
    var scriptIndex = afterHead.search(/<script\b/i);
    var beforeScript = scriptIndex >= 0 ? afterHead.slice(0, scriptIndex) : afterHead;
    var fromScript = scriptIndex >= 0 ? afterHead.slice(scriptIndex) : "";
    var bodyTag = (beforeScript.match(/<body\b[^>]*>/i) || [])[0] || "";
    var newBodyTag = buildViewerModeBodyTag(bodyTag);
    if (!bodyTag || newBodyTag === bodyTag) return source;
    return head + "</head>" + beforeScript.replace(bodyTag, newBodyTag) + fromScript;
  }

  function repairBrokenScriptLiterals(html) {
    var out = String(html || "");
    out = out.replace(
      /'  <script>window\.APP_MODE = "view";<\/script>\\n'/g,
      "'  <scr' + 'ipt>window.APP_MODE = \"view\";</scr' + 'ipt>\\n'"
    );
    out = out.replace(
      /\n  <script>window\.APP_MODE = "view";<\/script>\n/g,
      "\n  <scr" + "ipt>window.APP_MODE = \"view\";</scr" + "ipt>\n"
    );
    out = out.replace(
      /`  <!--viewer-build:[^`]+-->\n  <!--viewer-deploy-boot-->\n  <script>window\.APP_MODE = "view";<\/script>\n`/g,
      function (block) {
        return block
          .replace("<script>", "<scr" + "ipt>")
          .replace("</script>", "</scr" + "ipt>");
      }
    );
    return out;
  }

  function ensureViewerDeployScriptClosed(html) {
    var out = String(html || "");
    var openMatch = getViewerMainScriptOpenMatch(out);
    var bodyClose = getViewerBodyCloseIndex(out);
    if (!openMatch || bodyClose < 0) return out;
    var region = out.slice(openMatch.index, bodyClose);
    if (region.indexOf(SCRIPT_CLOSE) < 0) {
      out = out.slice(0, bodyClose) + "\n  " + SCRIPT_CLOSE + "\n" + out.slice(bodyClose);
    }
    return out;
  }

  function finalizeViewerDeployIndexHtml(html) {
    var out = repairBrokenScriptLiterals(html);
    out = ensureViewerDeployScriptClosed(out);
    return out;
  }

  function prepareViewerDeployIndexHtml(html) {
    var out = ensureViewerModeBodyClass(finalizeViewerDeployIndexHtml(html));
    var headHtml = out.split("</head>", 1)[0];
    if (headHtml.indexOf("<!--viewer-deploy-boot-->") < 0) {
      var buildStamp = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
      var boot =
        "  <!--viewer-build:" + buildStamp + "-->\n" +
        "  <!--viewer-deploy-boot-->\n" +
        "  <scr" + "ipt>window.APP_MODE = \"view\";</scr" + "ipt>\n";
      out = out.replace(/<\/head>/i, boot + "</head>");
    }
    out = out.replace(
      /<title>[^<]*<\/title>/i,
      "<title>\u30c8\u30fc\u30ca\u30e1\u30f3\u30c8 \u30bf\u30a4\u30e0\u30c6\u30fc\u30d6\u30eb\uff08\u95b2\u89a7\uff09</title>"
    );
    return finalizeViewerDeployIndexHtml(out);
  }

  function getViewerBuildStamp(html) {
    var headHtml = String(html || "").split("</head>", 1)[0];
    var match = headHtml.match(/<!--viewer-build:([^>]+)-->/);
    return match ? match[1] : "";
  }

  function validateViewerDeployIndexHtml(html) {
    var source = finalizeViewerDeployIndexHtml(html);
    var head = source.split("</head>", 1)[0];
    var bodyTag = getViewerBodyTag(source);
    var errors = [];
    if (head.indexOf("<!--viewer-deploy-boot-->") < 0) {
      errors.push("viewer \u8d77\u52d5\u30b9\u30af\u30ea\u30d7\u30c8\u304c\u3042\u308a\u307e\u305b\u3093");
    }
    if (!bodyTag || !/\bviewer-mode\b/.test(bodyTag)) {
      errors.push("body.viewer-mode \u304c\u3042\u308a\u307e\u305b\u3093");
    }
    if (!getViewerMainScriptOpenMatch(source)) {
      errors.push("\u30e1\u30a4\u30f3 script \u304c\u3042\u308a\u307e\u305b\u3093");
    } else if (getViewerMainScriptCloseEnd(source) < 0) {
      errors.push("script \u304c\u9589\u3058\u3089\u308c\u3066\u3044\u307e\u305b\u3093");
    } else {
      var tail = getViewerHtmlTailAfterMainScript(source);
      if (/setupViewerMode|\$\{escapeHtml|function\s+prepareViewerDeployIndexHtml/.test(tail)) {
        errors.push("JS \u304c\u30da\u30fc\u30b8\u4e0b\u90e8\u306b\u6f0f\u308c\u51fa\u3057\u3066\u3044\u307e\u3059");
      }
    }
    if (errors.length) {
      throw new Error(
        "\u95b2\u89a7\u7528 index.html \u306e\u691c\u8a3c\u306b\u5931\u6557: " +
        errors.join("\u3001") +
        "\u3002\u7ba1\u7406\u753b\u9762\u3092\u518d\u8aad\u307f\u8fbc\u307f\u3057\u3066\u304b\u3089\u300c\u751f\u6210\u300d\u3059\u308b\u304b\u3001./build-viewer-zip.sh \u3092\u4f7f\u3063\u3066\u304f\u3060\u3055\u3044\u3002"
      );
    }
    return source;
  }

  var ZIP_CRC32_TABLE = (function () {
    var table = new Uint32Array(256);
    for (var i = 0; i < 256; i++) {
      var c = i;
      for (var j = 0; j < 8; j++) {
        c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[i] = c >>> 0;
    }
    return table;
  })();

  function crc32Bytes(data) {
    var crc = 0xffffffff;
    for (var i = 0; i < data.length; i++) {
      crc = ZIP_CRC32_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function createZipBlob(entries) {
    var localParts = [];
    var centralParts = [];
    var offset = 0;

    for (var e = 0; e < entries.length; e++) {
      var entry = entries[e];
      var nameBytes = new TextEncoder().encode(entry.name);
      var data = entry.data;
      var crc = crc32Bytes(data);

      var localHeader = new Uint8Array(30 + nameBytes.length);
      var localView = new DataView(localHeader.buffer);
      localView.setUint32(0, 0x04034b50, true);
      localView.setUint16(4, 20, true);
      localView.setUint16(6, 0, true);
      localView.setUint16(8, 0, true);
      localView.setUint16(10, 0, true);
      localView.setUint16(12, 0, true);
      localView.setUint32(14, crc, true);
      localView.setUint32(18, data.length, true);
      localView.setUint32(22, data.length, true);
      localView.setUint16(26, nameBytes.length, true);
      localView.setUint16(28, 0, true);
      localHeader.set(nameBytes, 30);
      localParts.push(localHeader, data);

      var centralHeader = new Uint8Array(46 + nameBytes.length);
      var centralView = new DataView(centralHeader.buffer);
      centralView.setUint32(0, 0x02014b50, true);
      centralView.setUint16(4, 20, true);
      centralView.setUint16(6, 20, true);
      centralView.setUint16(8, 0, true);
      centralView.setUint16(10, 0, true);
      centralView.setUint16(12, 0, true);
      centralView.setUint16(14, 0, true);
      centralView.setUint32(16, crc, true);
      centralView.setUint32(20, data.length, true);
      centralView.setUint32(24, data.length, true);
      centralView.setUint16(28, nameBytes.length, true);
      centralView.setUint16(30, 0, true);
      centralView.setUint16(32, 0, true);
      centralView.setUint16(34, 0, true);
      centralView.setUint16(36, 0, true);
      centralView.setUint32(38, 0, true);
      centralView.setUint32(42, offset, true);
      centralHeader.set(nameBytes, 46);
      centralParts.push(centralHeader);

      offset += localHeader.length + data.length;
    }

    var centralSize = centralParts.reduce(function (sum, part) { return sum + part.length; }, 0);
    var endRecord = new Uint8Array(22);
    var endView = new DataView(endRecord.buffer);
    endView.setUint32(0, 0x06054b50, true);
    endView.setUint16(8, entries.length, true);
    endView.setUint16(10, entries.length, true);
    endView.setUint32(12, centralSize, true);
    endView.setUint32(16, offset, true);
    endView.setUint16(20, 0, true);

    return new Blob([].concat(localParts, centralParts, [endRecord]), { type: "application/zip" });
  }

  async function fetchViewerDeployText(path) {
    var bases = [];
    if (location.protocol.indexOf("http") === 0) {
      bases.push(new URL("./", location.href).href);
    }
    bases.push(EDITOR_SITE_ORIGIN.replace(/\/$/, "") + "/");

    for (var i = 0; i < bases.length; i++) {
      try {
        var url = new URL(path, bases[i]);
        url.searchParams.set("_", String(Date.now()));
        var res = await fetch(url, { cache: "no-store" });
        if (res.ok) return await res.text();
      } catch (_err) {}
    }

    if (VIEWER_DEPLOY_FALLBACKS[path]) return VIEWER_DEPLOY_FALLBACKS[path];
    throw new Error(
      path + " \u306e\u53d6\u5f97\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u3002\u7ba1\u7406\u753b\u9762\uff08" +
      EDITOR_SITE_ORIGIN + "\uff09\u304b\u3089\u5b9f\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
    );
  }

  async function getViewerDeployIndexHtml() {
    var source = await fetchViewerDeployText("index.html");
    return prepareViewerDeployIndexHtml(source);
  }

  async function buildZip(jsonText) {
    var indexHtml = validateViewerDeployIndexHtml(await getViewerDeployIndexHtml());
    var viewHtml = await fetchViewerDeployText("view.html");
    var netlifyToml = await fetchViewerDeployText("netlify.toml");
    return {
      blob: createZipBlob([
        { name: "index.html", data: new TextEncoder().encode(indexHtml) },
        { name: "view.html", data: new TextEncoder().encode(viewHtml) },
        { name: "netlify.toml", data: new TextEncoder().encode(netlifyToml) },
        { name: "_redirects", data: new TextEncoder().encode(VIEWER_DEPLOY_REDIRECTS) },
        { name: PUBLISHED_JSON_PATH, data: new TextEncoder().encode(jsonText) }
      ]),
      buildStamp: getViewerBuildStamp(indexHtml)
    };
  }

  window.__sanitizeViewerDeploySource = finalizeViewerDeployIndexHtml;
  window.ViewerDeploy = {
    buildZip: buildZip,
    finalizeViewerDeployIndexHtml: finalizeViewerDeployIndexHtml,
    prepareViewerDeployIndexHtml: prepareViewerDeployIndexHtml,
    validateViewerDeployIndexHtml: validateViewerDeployIndexHtml
  };
})();
