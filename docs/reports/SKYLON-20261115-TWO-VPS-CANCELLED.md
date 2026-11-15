# SkylonHost: new test VPS cancelled

Date: 2026-11-15. Branch: sk1114. Previous checkpoint: 439dc9e445098af5ca22ef70d994d639e577d9cf.

The user reported that both new VPS work on Beeline home Wi-Fi but fail on Megafon Moscow and Beeline Moscow mobile networks, and explicitly requested cancelling both new test VPS while retaining the first VPS.

## Completed

- Sky2 / tetss-prague-ip2-test / 109.248.43.149 / instance 9d72247c-7039-4d6d-8419-103111678741: Destroy submitted and removal verified in the provider overview.
- Sky3 / tetss-prague-ip3-test / 109.248.43.30 / instance 3751425a-75a0-40ed-bd10-828307f984bd: Destroy submitted and removal verified in the provider overview.
- The final provider overview contains only tetss-prague-test / 109.248.43.81 / instance e6fa65c1-e10a-4123-9f89-83d522483254, status Running. Its configuration was not changed.

The two test services were destroyed, not merely powered off. Their former combined hourly rate was EUR 0.018. The provider billing page showed EUR 0.252 usage in November and EUR 4.74 current balance (displayed precision); no itemized final cancellation receipt was exposed on that page. The retained VPS remains billable.

## Scope and validation

Verification used the authenticated provider dashboard and final instance inventory. No other hosting providers, Connect app, DNS, subscriptions or users were modified. Prior Sky2/Sky3 keys and QR codes no longer correspond to active servers and must not be distributed as working connections. No secrets included in this report. PR and CI are not applicable to provider-console cancellation.

## Next checkpoint

Retain only the first SkylonHost VPS until the user decides otherwise. No further user action is required for these two cancellations. This report supersedes the earlier two-VPS-ready report for active inventory.
