import http from 'k6/http';
import {check, sleep} from 'k6';

export const options = {
  vus: 2,
  iterations: 6,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1600']
  }
};

const backendUrl = __ENV.BACKEND_URL || 'http://127.0.0.1:8091';
const webUrl = __ENV.WEB_URL || 'http://127.0.0.1:3000';

export default function () {
  const responses = [
    http.get(`${backendUrl}/health/live`),
    http.get(`${backendUrl}/health/ready`),
    http.get(`${backendUrl}/api/v1/meta/system-mode`),
    http.get(`${backendUrl}/api/v1/public/catalog/items`),
    http.get(`${webUrl}/`),
    http.get(`${webUrl}/login`),
    http.get(`${webUrl}/marketing`),
    http.get(`${webUrl}/request-workbench`),
    http.get(`${webUrl}/orders`),
    http.get(`${webUrl}/suppliers`)
  ];

  responses.forEach((response) => {
    check(response, {
      'status is 200': (r) => r.status === 200
    });
  });

  sleep(1);
}
