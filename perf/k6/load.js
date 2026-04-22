import http from 'k6/http';
import {check, sleep} from 'k6';

export const options = {
  stages: [
    {duration: '30s', target: 10},
    {duration: '1m', target: 25},
    {duration: '30s', target: 0}
  ],
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<1800']
  }
};

const backendUrl = __ENV.BACKEND_URL || 'http://127.0.0.1:8091';
const webUrl = __ENV.WEB_URL || 'http://127.0.0.1:3000';

export default function () {
  const response = http.batch([
    ['GET', `${backendUrl}/health/ready`],
    ['GET', `${backendUrl}/api/v1/meta/system-mode`],
    ['GET', `${backendUrl}/api/v1/public/catalog/items`],
    ['GET', `${webUrl}/`],
    ['GET', `${webUrl}/marketing`],
    ['GET', `${webUrl}/request-workbench`],
    ['GET', `${webUrl}/orders`],
    ['GET', `${webUrl}/suppliers`]
  ]);

  response.forEach((item) => {
    check(item, {
      'load status is 200': (r) => r.status === 200
    });
  });

  sleep(1);
}
