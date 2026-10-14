"""Pure synthetic metric generation; persistence belongs inside the execution transaction."""
import hashlib
import random


def synthetic_metrics(campaign_id,counts,seed=17):
    rows=[]
    for persona in sorted(counts):
        n=counts[persona]
        rng=random.Random(int(hashlib.sha256(f'{seed}:{campaign_id}:{persona}'.encode()).hexdigest()[:12],16))
        opened=sum(rng.random()<.43 for _ in range(n))
        clicked=sum(rng.random()<.12 for _ in range(opened))
        unsub=sum(rng.random()<.01 for _ in range(n))
        rows.append(dict(persona=persona,recipient_count=n,simulated_deliveries=n,
                         opened=opened,clicked=clicked,unsubscribed=unsub,source_type='SYNTHETIC',
                         open_rate=round(opened/n,4) if n else 0,
                         click_rate=round(clicked/n,4) if n else 0))
    return rows

def hypothesis_summary(rows):
    return (f'DEMO ONLY: {sum(x["recipient_count"] for x in rows)} synthetic recipients. '
            'Simulated events do not demonstrate conversion lift, causal improvement, '
            'real email delivery, or market performance. Next step: connect consented '
            'campaign events, define a measurement window and test a preregistered hypothesis.')
