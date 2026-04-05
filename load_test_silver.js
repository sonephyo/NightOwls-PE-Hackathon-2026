import http from 'k6/http';
import { check, sleep } from 'k6';

// Silver tier: 200 concurrent users for 2 minutes
// Traffic goes through Nginx → 2 app replicas (horizontal scaling)
export const options = {
  vus: 200,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // Silver requirement: under 3 seconds
    http_req_failed: ['rate<0.05'],      // error rate under 5%
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
