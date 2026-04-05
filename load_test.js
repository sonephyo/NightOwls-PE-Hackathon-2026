import http from 'k6/http';
import { check, sleep } from 'k6';

// Test configuration: 50 concurrent users for 1 minute
// Run: k6 run load_test.js -e TARGET=http://159.203.122.103
export const options = {
  vus: 50,        // 50 concurrent virtual users
  duration: '1m', // run for 1 minute
  thresholds: {
    http_req_duration: ['p(95)<500'],  // Bronze: p95 under 500ms
    http_req_failed: ['rate<0.05'],     // error rate under 5%
  },
};

// Sample short codes from the seed data (urls.csv)
const shortCodes = [
  '0Y7puX', 'joOewJ', 'YMwcJp', 'gHOkuS',
  'IKhHtb', 'wx48gY', '1U9mdL', 'Uk5jxw',
  'yQSwT2', '3mgDRW', 'VgkwPM', 'H8r4XJ', 'afSvrh', 'ANQfSc'
];

const BASE_URL = __ENV.TARGET || 'https://night-owls.duckdns.org';

export default function () {
  // Pick a random short code from the list
  const shortCode = shortCodes[Math.floor(Math.random() * shortCodes.length)];
  
  // Test the URL redirect endpoint (core functionality)
  const response = http.get(`${BASE_URL}/${shortCode}`, {
    redirects: 0, // Don't follow redirects, just check the response
  });
  
  // Verify the response
  check(response, {
    'redirect or not found': (r) => r.status === 301 || r.status === 302 || r.status === 404 || r.status === 410,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  // Add think time between requests (1 second)
  sleep(1);
}
