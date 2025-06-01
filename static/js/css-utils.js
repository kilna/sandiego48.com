function formatClock(days, hours, minutes, seconds) {
  var clock = "<span class=\"clock\">"
    + "<span class=\"off\">88:88:88</span>"
    + "<span class=\"on\">"
    + hours.toString().padStart(2, '0') + ":"
    + minutes.toString().padStart(2, '0') + ":"
    + seconds.toString().padStart(2, '0')
    + "</span></span>";
  if (days > 0) {
    clock = (
      "<span class=\"clock\">"
      + "<span class=\"off\">888</span>"
      + "<span class=\"on\">"
      + days.toString().padStart(3, ' ').replace(/ /g, '<span class="zero">0</span>')
      + "</span>"
      + "</span>"
      + " days "
      + clock
    );
  }
  return clock;
}

function getRandomCountdown() {
  return {
    days: Math.floor(Math.random() * 365),
    hours: Math.floor(Math.random() * 24),
    minutes: Math.floor(Math.random() * 60),
    seconds: Math.floor(Math.random() * 60)
  };
}

function getCurrentCountdown(targetTime) {
  var elapsed = targetTime - Date.now();
  var days = Math.floor(elapsed / (1000 * 60 * 60 * 24));
  var hours = Math.floor((elapsed % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  var minutes = Math.floor((elapsed % (1000 * 60 * 60)) / (1000 * 60));
  var seconds = Math.floor((elapsed % (1000 * 60)) / 1000);
  return { days: days, hours: hours, minutes: minutes, seconds: seconds };
}

function parseTimeClass(className, prefix) {
  if (!className.startsWith(prefix)) return null;
  
  // Convert from URL-safe format back to ISO format
  const timeStr = className.replace(prefix, '');
  
  // Parse the date and time components
  const [datePart, timePart] = timeStr.split('T');
  const [year, month, day] = datePart.split('-');
  
  // Check if timezone is present
  const tzMatch = timePart.match(/([+-]\d{2}:\d{2})$/);
  let hour, minute, second;
  
  if (tzMatch) {
    // Parse time with timezone
    const [time, tz] = timePart.split(/([+-]\d{2}:\d{2})$/);
    [hour, minute, second] = time.split(':');
    
    // Parse timezone offset
    const [_, sign, tzHours, tzMinutes] = tz.match(/([+-])(\d{2}):(\d{2})/);
    const tzOffset = (parseInt(tzHours) * 60 + parseInt(tzMinutes)) * 60 * 1000 * (sign === '+' ? 1 : -1);
    
    // Create date in UTC by using Date.UTC and adjusting for timezone
    return Date.UTC(year, month - 1, day, hour, minute, second) - tzOffset;
  } else {
    // Parse time without timezone (assume local time)
    [hour, minute, second] = timePart.split(':');
    const date = new Date(year, month - 1, day, hour, minute, second);
    return date.getTime();
  }
}

function startCountdown(element) {
  const classes = element.className.split(' ');
  let targetTime = null;
  
  // Find the countdown-to- class
  for (const className of classes) {
    targetTime = parseTimeClass(className, 'countdown-to-');
    if (targetTime !== null) break;
  }
  
  if (!targetTime) return;
  
  var animationStart = Date.now();
  function updateCountdown() {
    var t = getCurrentCountdown(targetTime);
    element.innerHTML = formatClock(t.days, t.hours, t.minutes, t.seconds);
  }
  function startRealCountdown() {
    updateCountdown();
    return setInterval(updateCountdown, 1000);
  }
  var animationInterval = setInterval(function() {
    if (Date.now() - animationStart > 500) {
      clearInterval(animationInterval);
      startRealCountdown();
      return;
    }
    var t = getRandomCountdown();
    element.innerHTML = formatClock(t.days, t.hours, t.minutes, t.seconds);
  }, 10);
}

// Initialize all countdown timers on page load
document.addEventListener('DOMContentLoaded', function() {
  // Find all elements with countdown-to- classes and start the countdown
  const countdownElements = document.querySelectorAll('[class*="countdown-to-"]');
  countdownElements.forEach(startCountdown);

  // Find all elements with visibility time classes
  const elements = document.querySelectorAll('[class*="visible-after-"], [class*="visible-until-"]');
  
  elements.forEach(element => {
    const classes = element.className.split(' ');
    let visibleAfter = null;
    let visibleUntil = null;
    
    // Extract time classes
    for (const className of classes) {
      if (!visibleAfter) {
        const afterTime = parseTimeClass(className, 'visible-after-');
        if (afterTime !== null) visibleAfter = afterTime;
      }
      if (!visibleUntil) {
        const untilTime = parseTimeClass(className, 'visible-until-');
        if (untilTime !== null) visibleUntil = untilTime;
      }
      if (visibleAfter && visibleUntil) break;
    }
    
    const now = Date.now();
    
    // Check if element should be visible initially
    const shouldBeVisible = (!visibleAfter || now >= visibleAfter) && (!visibleUntil || now < visibleUntil);
    
    if (!shouldBeVisible) {
      element.style.display = 'none';
      
      // Set up an interval to check every minute
      const checkInterval = setInterval(() => {
        const currentTime = Date.now();
        const shouldShow = (!visibleAfter || currentTime >= visibleAfter) && (!visibleUntil || currentTime < visibleUntil);
        
        if (shouldShow) {
          element.style.display = '';  // Show element by removing inline style
          clearInterval(checkInterval);  // Stop checking once visible
        } else if (visibleUntil && currentTime >= visibleUntil) {
          clearInterval(checkInterval);
        }
      }, 1000);  // Check every minute
    } else {
      element.style.display = '';
    }
  });
}); 
