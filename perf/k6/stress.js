import http from 'k6/http';
import {check, sleep} from 'k6';

export const options = {
  stages: [
    {duration: '30s', target: 25},
    {duration: '30s', target: 75},
    {duration: '1m', target: 100},
    {duration: '30s', target: 0}
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<2500']
  }
};

const backendUrl = __ENV.BACKEND_URL || 'http://127.0.0.1:8091';
const webUrl = __ENV.WEB_URL || 'http://127.0.0.1:3000';

export default function () {
  const response = http.batch([
    ['GET', `${backendUrl}/health`],
    ['GET', `${backendUrl}/status`],
    ['GET', `${backendUrl}/companies?limit=20`],
    ['GET', `${webUrl}/`],
    ['GET', `${webUrl}/project-map`],
    ['GET', `${webUrl}/ui/companies`]
  ]);

  response.forEach((item) => {
    check(item, {
      'stress status is 200': (r) => r.status === 200
    });
  });

  sleep(1);
}
