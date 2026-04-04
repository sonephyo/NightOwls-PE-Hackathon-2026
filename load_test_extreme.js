import http from 'k6/http';
import { check, sleep } from 'k6';

// Extreme tier: 1000 concurrent users for 2 minutes
// Beyond the quest requirements — stress testing the limits of the stack.
export const options = {
  stages: [
    { duration: '20s', target: 1000 },  // ramp up to 1000
    { duration: '2m',  target: 1000 },  // hold at 1000
    { duration: '10s', target: 0    },  // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.05'],
  },
};

const shortCodes = [
  '0Y7puX', 'joOewJ', 'YMwcJp', 'gHOkuS',
  'IKhHtb', 'wx48gY', '1U9mdL', 'Uk5jxw',
  'yQSwT2', '3mgDRW', 'VgkwPM', 'H8r4XJ', 'afSvrh', 'ANQfSc'
];

const BASE_URL = 'http://localhost:8000';

export default function () {
  const shortCode = shortCodes[Math.floor(Math.random() * shortCodes.length)];

  const response = http.get(`${BASE_URL}/${shortCode}`, {
    redirects: 0,
  });

  check(response, {
    'redirect or not found': (r) => r.status === 302 || r.status === 404 || r.status === 410,
    'response time < 3000ms': (r) => r.timings.duration < 3000,
  });

  sleep(1);
}
