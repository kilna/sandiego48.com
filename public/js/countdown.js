function setCountdown(timeString, setElementId, hideElementId) {
    var timeObj = new Date(timeString).getTime();
    var intervalObj = setInterval(function() {
        var elapsed = timeObj - new Date().getTime();
        var days = Math.floor(elapsed / (1000 * 60 * 60 * 24));
        var hours = Math.floor((elapsed % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        var minutes = Math.floor((elapsed % (1000 * 60 * 60)) / (1000 * 60));
        var seconds = Math.floor((elapsed % (1000 * 60)) / 1000);
        document.getElementById(setElementId).innerHTML = (
          days + " days "
          + hours + " hours "
          + minutes + " minutes "
          + seconds + " seconds"
        );
        if (elapsed < 0) {
          clearInterval(intervalObj);
          document.getElementById(hideElementId).style.display = 'none';
        }
        else {
          document.getElementById(hideElementId).style.display = 'block';
        }
    }, 1000);
}
