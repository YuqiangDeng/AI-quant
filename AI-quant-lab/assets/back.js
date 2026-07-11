/* AI-quant-lab 看板页返回浮标
   用法：看板 </body> 前加入
     <script>window.__BASE="../";</script>
     <script src="../assets/back.js"></script> */
(function () {
  var BASE = window.__BASE || "../";
  var a = document.createElement("a");
  a.className = "site-back";
  a.href = BASE + "index.html";
  a.textContent = "🏠 作品集";
  a.setAttribute("title", "返回作品集首页");
  document.body.appendChild(a);
})();
