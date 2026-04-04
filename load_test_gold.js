import http from 'k6/http';
import { check, sleep } from 'k6';

// Gold tier: 500 concurrent users for 2 minutes
// Redis caching means popular short codes skip the DB entirely.
export const options = {
  vus: 500,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // keep p95 under 3 seconds
    http_req_failed: ['rate<0.05'],      // Gold requirement: under 5% errors
  },
};

const shortCodes = [
  '0Y7puX', 'joOewJ', 'YMwcJp', 'gHOkuS', 'aPgkMG',
  'IKhHtb', '6mStl9', 'wx48gY', '1U9mdL', 'Uk5jxw',
  'jHH6Rw', 'yQSwT2', 'ULUAiE', '3mgDRW', 'xwMpkA',
  'VgkwPM', 'H8r4XJ', 'afSvrh', 'ANQfSc'
];

const BASE_URL = 'http://localhost:8000';

export default function () {
  const shortCode = shortCodes[Math.floor(Math.random() * shortCodes.length)];

  const response = http.get(`${BASE_URL}/${shortCode}`, {
    redirects: 0,
  });

  check(response, {
    'redirect or not found': (r) => r.status === 302 || r.status === 404,
    'response time < 3000ms': (r) => r.timings.duration < 3000,
  });

  sleep(1);
}
