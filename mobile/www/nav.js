// Highlight the active navigation link based on current page
(function(){
  function highlightActive(){
    var page = location.pathname.split('/').pop();
    document.querySelectorAll('.bottom-nav a').forEach(function (link){
      if (link.getAttribute('href') === page){
        link.classList.add('active');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    highlightActive();
  });
})();
