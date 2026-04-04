import http from 'k6/http';
import { check, sleep } from 'k6';

// Test configuration: 200 concurrent users for 1 minute
export const options = {
  vus: 200,        // 200 concurrent virtual users
  duration: '1m', // run for 1 minute
};

// Sample short codes from the CSV data
const shortCodes = [
  '0Y7puX', 'joOewJ', 'YMwcJp', 'gHOkuS', 'aPgkMG', 
  'IKhHtb', '6mStl9', 'wx48gY', '1U9mdL', 'Uk5jxw',
  'jHH6Rw', 'yQSwT2', 'ULUAiE', '3mgDRW', 'xwMpkA',
  'VgkwPM', 'H8r4XJ', 'afSvrh', 'ANQfSc'
];

function getRandomShortCode() {
  const index = Math.floor(Math.random() * shortCodes.length);
  return shortCodes[index];
}

export default function () {
  const shortCode = getRandomShortCode();
  
  // Test against nginx load balancer on port 80
  const res = http.get(`http://localhost/${shortCode}`, {
    redirects: 0  // Don't follow redirects - we just want to check the 302
  });
  
  check(res, {
    'redirect or not found': (r) => r.status === 302 || r.status === 404,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
