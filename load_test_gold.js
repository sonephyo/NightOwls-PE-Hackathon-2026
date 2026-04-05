import http from 'k6/http';
import { check, sleep } from 'k6';

// Gold tier: 500 concurrent users for 2 minutes
// Redis caching means popular short codes skip the DB entirely.
export const options = {
  stages: [
    { duration: '20s', target: 500 },  // ramp up to 500
    { duration: '2m',  target: 500 },  // hold at 500
    { duration: '10s', target: 0   },  // ramp down
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

const BASE_URL = __ENV.TARGET || 'http://159.203.122.103';

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
