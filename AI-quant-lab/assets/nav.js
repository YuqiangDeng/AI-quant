/* AI-quant-lab 共享顶部导航 + 页脚
   用法：页面在 </body> 前加入
     <script>window.__BASE="../";</script>   // 相对站点根的路径前缀
     <script src="../assets/nav.js"></script>
   不传 window.__BASE 时默认 ""（站点根页面用）。 */
(function () {
  var BASE = window.__BASE || "";
  var REPO = "https://github.com/YuqiangDeng/AI-quant";

  var nav = document.createElement("header");
  nav.className = "site-nav";
  nav.innerHTML =
    '<a class="brand" href="' + BASE + 'index.html">📊 AI-quant-lab</a>' +
    '<nav class="nav-links">' +
      '<a href="' + BASE + 'index.html">首页</a>' +
      '<a href="' + BASE + 'task1/index.html">Task1</a>' +
      '<a href="' + BASE + 'task2/index.html">Task2</a>' +
      '<a href="' + BASE + 'task3/task3_dashboard.html">Task3</a>' +
      '<a href="' + BASE + 'turtle-trading/task4_turtle_dashboard.html">Task4</a>' +
      '<a class="gh" href="' + REPO + '" target="_blank" rel="noopener">GitHub</a>' +
    '</nav>';
  document.body.insertBefore(nav, document.body.firstChild);

  var foot = document.createElement("footer");
  foot.className = "site-foot";
  foot.innerHTML =
    '<span>© 2026 邓宇强 · AI-quant-lab 量化作品集</span>' +
    '<span>由 WorkBuddy 小果 🦞 协助构建</span>';
  document.body.appendChild(foot);

  // 高亮当前页
  var here = location.pathname.replace(/\\/g, "/");
  nav.querySelectorAll("a").forEach(function (a) {
    var href = a.getAttribute("href") || "";
    if (href.indexOf("http") === 0) return;
    var target = (BASE + href).replace(/\.\.\//g, "");
    if (href !== "" && here.indexOf(target) !== -1 && target !== BASE + "index.html") {
      a.classList.add("active");
    }
  });
})();
