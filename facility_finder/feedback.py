"""Private product research, separate from public facility observations."""
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from facility_finder.enrichment import ROOT

DB = ROOT/'data/product-feedback.sqlite3'
PRESETS = {'Bundaran HI','Monas','Kota Tua','Blok M'}
TESTERS = ('Student','Commuter','Visitor','Caregiver','Other','Prefer not to say')
ANSWERS = ('Yes','Partly','No')
USEFUL = ('Yes','No','It was not shown')


def db_path():
    # An explicit override lets isolated browser QA avoid the live database.
    return Path(os.environ.get('LOKITO_FEEDBACK_DB',str(DB)))


def connect(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=10)
    conn.row_factory=sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS product_feedback (
        id INTEGER PRIMARY KEY, submission_id TEXT NOT NULL UNIQUE,
        submitted_at TEXT NOT NULL, schema_version INTEGER NOT NULL,
        ease TEXT NOT NULL CHECK(ease IN ('Yes','Partly','No')),
        location_understanding TEXT NOT NULL CHECK(location_understanding IN ('Yes','Partly','No')),
        venue_usefulness TEXT NOT NULL, photo_usefulness TEXT NOT NULL,
        comment TEXT NOT NULL CHECK(length(comment)<=1500),
        score INTEGER CHECK(score BETWEEN 1 AND 5), tester_type TEXT NOT NULL,
        facility_id TEXT, category TEXT, starting_preset TEXT,
        venue_shown INTEGER NOT NULL, photo_shown INTEGER NOT NULL,
        viewport_category TEXT)''')
    return conn


def submit(answers, context, valid_ids, submission_id, path=None):
    for key in ('ease','location_understanding'):
        if answers.get(key) not in ANSWERS: raise ValueError('Please answer the two questions about finding and locating a toilet.')
    for key in ('venue_usefulness','photo_usefulness'):
        if answers.get(key) not in USEFUL: raise ValueError('Please tell us whether the venue information and photo were useful.')
    if answers.get('tester_type') not in TESTERS: raise ValueError('Choose a tester type, or prefer not to say.')
    score=answers.get('score')
    if score is not None and (type(score) is not int or not 1<=score<=5): raise ValueError('Score must be 1–5 or left blank.')
    comment=answers.get('comment','')
    if not isinstance(comment,str) or len(comment.strip())>1500: raise ValueError('Please keep your comment within 1,500 characters.')
    fid=context.get('facility_id')
    if fid is not None and fid not in valid_ids: raise ValueError('The selected facility is no longer available.')
    if context.get('category') not in (None,'toilets','place_of_worship','drinking_water'): raise ValueError('Invalid category')
    if not isinstance(submission_id,str) or not 16<=len(submission_id)<=64: raise ValueError('Invalid submission token')
    preset=context.get('starting_preset')
    preset=preset if preset in PRESETS else None
    viewport=context.get('viewport_category')
    viewport=viewport if viewport in ('mobile','tablet','desktop') else None
    if not context.get('venue_shown') and answers['venue_usefulness'] != 'It was not shown':
        raise ValueError('No venue information was shown for this selection.')
    if not context.get('photo_shown') and answers['photo_usefulness'] != 'It was not shown':
        raise ValueError('No photo was shown for this selection.')
    values=(submission_id,datetime.now(timezone.utc).isoformat(),1,answers['ease'],answers['location_understanding'],
            answers['venue_usefulness'],answers['photo_usefulness'],comment.strip(),score,answers['tester_type'],
            fid,context.get('category'),preset,int(bool(context.get('venue_shown'))),int(bool(context.get('photo_shown'))),viewport)
    conn=connect(path or db_path())
    try:
        with conn:
            conn.execute('INSERT OR IGNORE INTO product_feedback (submission_id,submitted_at,schema_version,ease,location_understanding,venue_usefulness,photo_usefulness,comment,score,tester_type,facility_id,category,starting_preset,venue_shown,photo_shown,viewport_category) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values)
        return conn.execute('SELECT id FROM product_feedback WHERE submission_id=?',(submission_id,)).fetchone()[0]
    finally: conn.close()


def summary(path=None):
    target=Path(path or db_path())
    if not target.exists(): return {'total':0,'average_score':None,'scored':0,'distributions':{},'comments':[]}
    # Read-only connection: the owner dashboard cannot alter responses.
    conn=sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True)
    conn.row_factory=sqlite3.Row
    try:
        total=conn.execute('SELECT count(*) FROM product_feedback').fetchone()[0]
        scored,average=conn.execute('SELECT count(score),avg(score) FROM product_feedback').fetchone()
        fields=('ease','location_understanding','venue_usefulness','photo_usefulness')
        distributions={k:dict(conn.execute(f'SELECT {k},count(*) FROM product_feedback GROUP BY {k}').fetchall()) for k in fields}
        comments=[dict(r) for r in conn.execute("SELECT submitted_at,comment,score FROM product_feedback WHERE comment<>'' ORDER BY id DESC LIMIT 30")]
        return {'total':total,'average_score':average,'scored':scored,'distributions':distributions,'comments':comments}
    finally: conn.close()
