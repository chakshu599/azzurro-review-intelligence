from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Review, Property

SYDNEY=ZoneInfo("Australia/Sydney")

def week_bounds(now=None):
    now=(now or datetime.now(SYDNEY)).astimezone(SYDNEY)
    start=now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=now.weekday())
    end=start+timedelta(days=7)
    prev=start-timedelta(days=7)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc), prev.astimezone(timezone.utc)

async def filtered_reviews(db:AsyncSession, property_code=None, start=None, end=None):
    q=select(Review).join(Property)
    if property_code: q=q.where(Property.property_code==property_code)
    if start: q=q.where(Review.review_date>=start)
    if end: q=q.where(Review.review_date<end)
    q=q.order_by(Review.review_date.desc())
    result=await db.execute(q)
    return list(result.scalars().all())

def sentiment_counts(reviews):
    c={"positive":0,"negative":0,"neutral":0}
    for r in reviews:
        c[(r.sentiment or "neutral")]+=1
    return c

def avg_rating(reviews):
    vals=[r.rating for r in reviews if r.rating is not None and 1<=r.rating<=10]
    return round(sum(vals)/len(vals),2) if vals else None

def pct(n,d): return round(n/d*100,1) if d else 0.0

def aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

async def overview(db:AsyncSession, property_code=None, start=None,end=None):
    start=start or week_bounds()[2]
    end=end or datetime.now(timezone.utc)
    cur_start,cur_end,prev_start=week_bounds()
    allq=await filtered_reviews(db,property_code,start,end)
    current=await filtered_reviews(db,property_code,cur_start,cur_end)
    previous=await filtered_reviews(db,property_code,prev_start,cur_start)
    cur_s=sentiment_counts(current); prev_s=sentiment_counts(previous)
    cur_avg=avg_rating(current); prev_avg=avg_rating(previous)
    change=round(cur_avg-prev_avg,2) if cur_avg is not None and prev_avg is not None else None

    properties=(await db.execute(select(Property).order_by(Property.name))).scalars().all()
    comparison=[]
    volume=[]
    for prop in properties:
        if property_code and prop.property_code!=property_code: continue
        reviews=await filtered_reviews(db,prop.property_code,start,end)
        s=sentiment_counts(reviews)
        prop_prev=await filtered_reviews(db,prop.property_code,prev_start,cur_start)
        prop_cur=await filtered_reviews(db,prop.property_code,cur_start,cur_end)
        pa=avg_rating(prop_prev); ca=avg_rating(prop_cur)
        complaint=self_topic_top(reviews,"negative")
        comparison.append({"property":prop.name,"avg_rating":avg_rating(reviews),"total_reviews":len(reviews),"positive_pct":pct(s["positive"],len(reviews)),"negative_pct":pct(s["negative"],len(reviews)),"complaint":complaint,"week_change":round(ca-pa,2) if ca is not None and pa is not None else None})
        volume.append({"property":prop.name,"reviews":len(reviews)})

    topic_dist=[]
    negatives=[r for r in allq if r.sentiment=="negative"]
    counts=defaultdict(int)
    for r in negatives:
        for item in (r.topics or []):
            counts[item.get("topic")]+=1
    for topic,count in sorted(counts.items(),key=lambda x:x[1],reverse=True):
        topic_dist.append({"topic":topic,"count":count,"percentage":pct(count,len(negatives))})

    pos_trend=[]
    negative_trend=[]
    weekly=[]
    d=cur_start
    while d<cur_end:
        day_end=d+timedelta(days=1)
        rs=[r for r in current if r.review_date and d<=aware(r.review_date)<day_end]
        sc=sentiment_counts(rs)
        pos_trend.append({"week":d.strftime("%a"),"positive":sc["positive"],"negative":sc["negative"]})
        weekly.append({"week":d.strftime("%a"),"rating":avg_rating(rs) or 0})
        d=day_end

    source="synthetic" if allq and any((r.source_url or "").startswith("demo:") for r in allq) else ("booking.com" if allq and any("booking.com" in (r.source_url or "") for r in allq) else ("csv_import" if allq else "none"))
    kpis=[
        {"label":"Average guest rating this week","value":cur_avg or 0,"change":change,"change_direction":"up" if change and change>0 else "down" if change and change<0 else "flat"},
        {"label":"Previous week's average rating","value":prev_avg or 0},
        {"label":"Rating change vs previous week","value":change or 0,"change_direction":"up" if change and change>0 else "down" if change and change<0 else "flat"},
        {"label":"Total reviews this week","value":len(current),"change":len(current)-len(previous),"change_direction":"up" if len(current)>len(previous) else "down" if len(current)<len(previous) else "flat"},
        {"label":"Positive reviews","value":cur_s["positive"]},
        {"label":"Negative reviews","value":cur_s["negative"]},
        {"label":"Neutral reviews","value":cur_s["neutral"]},
        {"label":"Overall sentiment","value":pct(cur_s["positive"],len(current)),"change_direction":"flat"},
    ]
    return {"kpis":kpis,"weekly_trends":weekly,"pos_neg_trends":pos_trend,"property_comparison":comparison,"volume_by_property":volume,"topic_distribution":topic_dist,"date_range":{"start":cur_start.isoformat(),"end":cur_end.isoformat(),"timezone":"Australia/Sydney"},"data_source":source}

def self_topic_top(reviews, sentiment):
    counts=defaultdict(int)
    for r in reviews:
        if r.sentiment!=sentiment: continue
        for item in (r.topics or []):
            if item.get("sentiment")==sentiment:
                counts[item.get("topic")]+=1
    if not counts:return None
    return sorted(counts.items(),key=lambda x:x[1],reverse=True)[0][0]
