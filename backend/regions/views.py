from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .countries import MOBILE_RULES, SHORT_LIST, ordered
from .regions import CODES, as_api, region


class CountriesView(APIView):
    """
    GET: every country for phone pickers (Iraq first, then the Gulf short list,
    then A–Z), and the countries Wasel runs stores in with their currency,
    time zone, map centre and tip choices.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        regions = []
        for code in CODES:
            r = region(code)
            regions.append(
                {
                    "country": code,
                    "currency": r.currency,
                    "decimals": r.decimals,
                    "time_zone": r.time_zone,
                    "week_starts": r.week_starts,
                    "center": {"lat": r.center[0], "lng": r.center[1]},
                    "tips": [as_api(t, r.currency) for t in r.tips],
                }
            )
        return Response(
            {
                "short_list": SHORT_LIST,
                "countries": [
                    {"code": code, "dial": dial, "name_en": en, "name_ar": ar, "mobile": MOBILE_RULES.get(code)}
                    for code, dial, en, ar in ordered()
                ],
                "regions": regions,
            }
        )
