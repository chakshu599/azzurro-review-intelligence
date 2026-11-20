from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Property, Review, CollectionLog, make_hash
from app.schemas.schemas import *
from app.services.sentiment import get_analyzer
from app.services.topics import classify_topics
from app.services.analytics import overview, filtered_reviews, avg_rating, sentiment_counts, pct
from scraper.property_config import get_all_properties, get_property

router=APIRouter(prefix="/api")

@router.get("/health",response_model=HealthResponse)
async def health(db:AsyncSession=Depends(get_db)):
    try:
        await db.execute(select(func.count()).select_from(Property)); database="connected"
    except Exception as exc: database=f"error: {exc.__class__.__name__}"
    return HealthResponse(status="ok",version="1.0.0",database=database,timestamp=datetime.now(timezone.utc))

@router.get("/properties")
async def properties(db:AsyncSession=Depends(get_db)):
    r=await db.execute(select(Property).order_by(Property.name)); return r.scalars().all()

@router.get("/properties/{property_id}")
async def property_detail(property_id:str,db:AsyncSession=Depends(get_db)):
    q=select(Property).where(or_(Property.property_code==property_id,Property.id==int(property_id))) if property_id.isdigit() else select(Property).where(Property.property_code==property_id)
    r=await db.execute(q); prop=r.scalar_one_or_none()
    if not prop: raise HTTPException(404,"Property not found")
    reviews=await filtered_reviews(db,prop.property_code)
    sc=sentiment_counts(reviews)
    complaints={}; compliments={}
    for review in reviews:
        for item in (review.topics or []):
            bucket=complaints if item.get("sentiment")=="negative" else compliments if item.get("sentiment")=="positive" else None
            if bucket is not None:
                topic=item.get("topic")
                bucket[topic]=bucket.get(topic,0)+1
    to_rows=lambda d:[{"topic":k,"count":v,"percentage":pct(v,len(reviews))} for k,v in sorted(d.items(),key=lambda x:x[1],reverse=True)[:8]]
    recent=reviews[:10]
    return {"id":prop.id,"name":prop.name,"property_code":prop.property_code,"booking_url":prop.booking_url,"created_at":prop.created_at,"updated_at":prop.updated_at,"avg_rating":avg_rating(reviews),"total_reviews":len(reviews),"positive_pct":pct(sc["positive"],len(reviews)),"negative_pct":pct(sc["negative"],len(reviews)),"weekly_performance":[],"top_complaints":to_rows(complaints),"top_compliments":to_rows(compliments),"recent_reviews":[{"id":x.id,"external_review_id":x.external_review_id,"property_id":x.property_id,"review_date":x.review_date,"rating":x.rating,"positive_text":x.positive_text,"negative_text":x.negative_text,"language":x.language,"sentiment":x.sentiment,"sentiment_score":x.sentiment_score,"topics":x.topics,"source_url":x.source_url,"review_hash":x.review_hash,"collected_at":x.collected_at,"created_at":x.created_at} for x in recent],"recommendations":[f"Prioritise {k}: mentioned in {v} review(s)." for k,v in sorted(complaints.items(),key=lambda x:x[1],reverse=True)[:3]] or ["No recurring complaints detected in the available records."]}

@router.get("/reviews",response_model=ReviewListResponse)
async def reviews(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),property_code:Optional[str]=None,sentiment:Optional[str]=None,rating:Optional[int]=None,topic:Optional[str]=None,q:Optional[str]=None,sort:Optional[str]=Query("newest"),db:AsyncSession=Depends(get_db)):
    query=select(Review).join(Property)
    if property_code: query=query.where(Property.property_code==property_code)
    if sentiment: query=query.where(Review.sentiment==sentiment)
    if rating: query=query.where(Review.rating==rating)
    if topic: query=query.where(func.cast(Review.topics,db.bind.dialect.name == "sqlite" and "TEXT" or "TEXT").contains(topic))
    if q:
        like=f"%{q}%"; query=query.where(or_(Review.positive_text.ilike(like),Review.negative_text.ilike(like)))
    count_query=select(func.count()).select_from(query.subquery())
    total=(await db.execute(count_query)).scalar_one()
    query=query.order_by(Review.review_date.desc() if sort=="newest" else Review.review_date.asc())
    query=query.offset((page-1)*page_size).limit(page_size)
    rows=(await db.execute(query)).scalars().all()
    return ReviewListResponse(items=[ReviewResponse.model_validate(r) for r in rows],total=total,page=page,page_size=page_size)

@router.get("/reviews/{review_id}",response_model=ReviewResponse)
async def review_detail(review_id:int,db:AsyncSession=Depends(get_db)):
    r=await db.get(Review,review_id)
    if not r: raise HTTPException(404,"Review not found")
    return ReviewResponse.model_validate(r)

@router.get("/analytics/overview",response_model=OverviewResponse)
async def analytics_overview(property_code:Optional[str]=None,db:AsyncSession=Depends(get_db)):
    return OverviewResponse.model_validate(await overview(db,property_code))

@router.get("/analytics/properties")
async def analytics_properties(db:AsyncSession=Depends(get_db)): return (await overview(db))["property_comparison"]
@router.get("/analytics/trends")
async def analytics_trends(db:AsyncSession=Depends(get_db)): return {"weekly_rating":(await overview(db))["weekly_trends"],"positive_negative":(await overview(db))["pos_neg_trends"]}
@router.get("/analytics/sentiment")
async def analytics_sentiment(db:AsyncSession=Depends(get_db)): return sentiment_counts(await filtered_reviews(db))
@router.get("/analytics/topics")
async def analytics_topics(db:AsyncSession=Depends(get_db)): return (await overview(db))["topic_distribution"]

@router.get("/insights")
async def insights(db:AsyncSession=Depends(get_db),property_code:Optional[str]=None):
    ov=await overview(db,property_code)
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"items":[{"title":d["topic"],"body":f"{d['count']} negative review(s) mention this topic ({d['percentage']}%).","severity":"high" if d["percentage"]>=30 else "medium"} for d in ov["topic_distribution"]]}

@router.get("/collection/logs")
async def collection_logs(db:AsyncSession=Depends(get_db)):
    r=await db.execute(select(CollectionLog).order_by(CollectionLog.started_at.desc()).limit(100)); return r.scalars().all()

@router.get("/collection/status")
async def collection_status(db:AsyncSession=Depends(get_db)):
    r=await db.execute(select(CollectionLog).order_by(CollectionLog.started_at.desc()).limit(1)); log=r.scalar_one_or_none()
    return {"status":log.status if log else "idle","last_run":log.completed_at if log else None,"last_success":log.completed_at if log and log.status=="success" else None}

async def seed_properties(db:AsyncSession):
    for cfg in get_all_properties():
        r=await db.execute(select(Property).where(Property.property_code==cfg.property_code))
        if not r.scalar_one_or_none(): db.add(Property(name=cfg.name,property_code=cfg.property_code,booking_url=cfg.booking_url))
    await db.commit()

@router.post("/collection/run",response_model=CollectionRunResponse)
async def collection_run(payload:CollectionRunRequest,db:AsyncSession=Depends(get_db),x_admin_secret:Optional[str]=Header(None)):
    from app.config import settings
    if settings.admin_secret and x_admin_secret!=settings.admin_secret: raise HTTPException(401,"Admin secret required")
    await seed_properties(db)
    configs=[get_property(payload.property_code)] if payload.property_code else get_all_properties()
    configs=[c for c in configs if c]
    logs=[]
    for cfg in configs:
        prop=(await db.execute(select(Property).where(Property.property_code==cfg.property_code))).scalar_one()
        started=datetime.now(timezone.utc)
        log=CollectionLog(property_id=prop.id,status="failed",reviews_discovered=0,reviews_inserted=0,duplicates_skipped=0,invalid_skipped=0,errors=["Live collection is disabled until Playwright browser dependencies are configured. Use /api/reviews/import for imported or synthetic data."],started_at=started,completed_at=datetime.now(timezone.utc),duration_seconds=0.1)
        db.add(log); await db.commit(); await db.refresh(log); logs.append(CollectionLogResponse.model_validate(log))
    return CollectionRunResponse(status="failed",message="No live scraping was attempted; automate collection only in a configured browser environment with permitted access.",logs=logs)

@router.post("/reviews/import",response_model=ImportResponse)
async def import_reviews(payload:ImportRequest,db:AsyncSession=Depends(get_db),x_admin_secret:Optional[str]=Header(None)):
    from app.config import settings
    if settings.admin_secret and x_admin_secret!=settings.admin_secret: raise HTTPException(401,"Admin secret required")
    await seed_properties(db)
    analyzer=get_analyzer(); inserted=duplicates=invalid=0; errors=[]
    if payload.clear_existing:
        await db.execute(Review.__table__.delete())
    for record in payload.data:
        code=record.get("property_code")
        prop=(await db.execute(select(Property).where(Property.property_code==code))).scalar_one_or_none()
        if not prop: invalid+=1; errors.append(f"Unknown property_code: {code}"); continue
        try:
            rating=int(record["rating"])
            if not 1<=rating<=10: raise ValueError("rating must be 1-10")
            date=datetime.fromisoformat(str(record["review_date"]).replace("Z","+00:00"))
            if date.tzinfo is None: date=date.replace(tzinfo=timezone.utc)
        except Exception as exc: invalid+=1; errors.append(str(exc)); continue
        positive=record.get("positive_text") or None; negative=record.get("negative_text") or None
        combined=" ".join(x for x in (positive,negative) if x)
        if not combined: invalid+=1; errors.append("Review text is empty"); continue
        sentiment,score=analyzer.analyze(combined)
        text_topics=classify_topics(combined)
        ext=record.get("external_review_id")
        raw=f"{prop.id}|{date.isoformat()}|{rating}|{positive or ''}|{negative or ''}|{ext or ''}" 
        import hashlib
        h=hashlib.sha256(raw.encode()).hexdigest()
        existing=(await db.execute(select(Review).where(Review.review_hash==h))).scalar_one_or_none()
        if existing: duplicates+=1; continue
        db.add(Review(external_review_id=ext,property_id=prop.id,review_date=date.astimezone(timezone.utc),rating=rating,positive_text=positive,negative_text=negative,language=record.get("language"),sentiment=sentiment,sentiment_score=score,topics=text_topics,source_url=("demo:"+payload.source) if payload.source=="synthetic" else record.get("source_url") or "imported",review_hash=h))
        inserted+=1
    await db.commit()
    return ImportResponse(status="success",inserted=inserted,updated=0,duplicates_skipped=duplicates,invalid_skipped=invalid,errors=errors)
