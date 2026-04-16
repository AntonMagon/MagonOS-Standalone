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
    http.get(`${backendUrl}/health`),
    http.get(`${backendUrl}/status`),
    http.get(`${backendUrl}/companies?limit=5`),
    http.get(`${webUrl}/`),
    http.get(`${webUrl}/dashboard`),
    http.get(`${webUrl}/ops-workbench`),
    http.get(`${webUrl}/project-map`),
    http.get(`${webUrl}/ui/companies`)
  ];

  responses.forEach((response) => {
    check(response, {
      'status is 200': (r) => r.status === 200
    });
  });

  sleep(1);
}
