#!/bin/sh
# Pick up renewed certificates: reload nginx every 6 hours.
(while sleep 21600; do nginx -s reload; done) &
