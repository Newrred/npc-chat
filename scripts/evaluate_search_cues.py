"""Two-turn source-backed cue experiment; no application state writes."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=['timed', 'validation', 'active_topic'])
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output file')
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    from app.services.decision_service import DecisionService
    from app.conversation_memory import source_views
    from app.memory import retrieve
    from app.search_cues import cue_query
    from scripts.evaluate_identity_voice import CapturingCompletions
    cases = [
        ('movie', '영화 추천해줘', "영화는 '월터의 상상은 현실이 된다' 어때?", '좋아. 이걸로 정하자.', '그거 뭐였지?'),
        ('book', '책 추천해줘', "'도리언 그레이' 읽어봐.", '응 그걸 빌려볼게.', '그게 뭐였지?'),
        ('preference', '나는 복숭아를 좋아해.', '복숭아 좋아하는구나.', '응. 그 과일 정말 좋아.', '뭐였지'),
        ('shift', '영화 추천해줘', "영화는 '월터의 상상은 현실이 된다' 어때?", '근데 다른 얘기하자. 산책하기 좋은 날이네.', '오늘 저녁 뭐 먹지?'),
        ('unknown', '안녕', '반가워.', '벌써 8시네.', '어딜?')]
    if args.case == 'timed':
        cases = [('timed', '오늘 저녁 8시에 영화 보러갈까?', "좋아. 영화는 '월터의 상상은 현실이 된다' 어때?",
                  '어라 벌써 8시가 다 되어가네.', '어딜?')]
    if args.case in {'validation', 'active_topic'}:
        cases = [
            ('movie_new', '오늘 볼 영화 골라줘.', "영화는 '리틀 포레스트' 어때?", '네가 고른 작품으로 할래.', '그거 뭐였지?'),
            ('book_new', '주말에 읽을 책 골라줘.', "'모모' 읽어봐.", '네가 말한 걸 도서관에서 찾아볼래.', '그게 뭐였지?'),
            ('shift_implicit', '영화 추천해줘.', "영화는 '리틀 포레스트' 어때?",
             '영화 얘기는 그만하자. 이제 책상 위 물건을 정리하고 있어.', '그거 뭐였지?'),
            ('cancelled', '오늘 저녁 8시에 영화 보러갈까?', "좋아. 영화는 '리틀 포레스트' 어때?",
             '오늘 영화 약속은 취소야. 어디에도 안 갈 거야.', '어딜?')]
    service = DecisionService()
    capture = CapturingCompletions(service.client.chat.completions)
    service.client.chat.completions = capture
    report = {'experiment_id': 'EXP-12' if args.case == 'active_topic' else
              'EXP-11' if args.case == 'validation' else 'EXP-10',
              'rows':[],'cases':cases,'model':service.config.llm_model}
    try:
        for seed in (109,211):
            for case, user, assistant, bridge, query in cases:
                for enabled in ((False,) if args.case == 'active_topic' else (False,True)):
                    service.search_cue_experiment=enabled
                    capture.seed=seed
                    capture.raw=[]
                    row=dict(case=case,seed=seed,enabled=enabled)
                    try:
                        history=[dict(role='user',content=user),dict(role='assistant',content=assistant)]
                        first=service.decide(message=bridge,history=history,memories=[])
                        tail=[dict(role='user',content=bridge),dict(role='assistant',content=first.decision.reply)]
                        expanded=cue_query(query,first.search_cues) if enabled else query
                        sources=[dict(client_turn_id='source',user_message=user,decision={'reply':assistant})]
                        notes=source_views(sources,expanded,tail)
                        if case=='preference':
                            notes+=retrieve([dict(key='fruit',kind='preference',content=user,updated=1,importance=2)],expanded,tail)
                        second=service.decide(message=query,history=tail,memories=notes)
                        row.update(first=asdict(first),second=asdict(second),expanded=expanded,memories=notes,raw=capture.raw)
                        print(json.dumps(dict(case=case,seed=seed,enabled=enabled,cues=first.search_cues,memories=len(notes),reply=second.decision.reply),ensure_ascii=True),flush=True)
                    except Exception as exc:
                        row.update(error=type(exc).__name__,raw=capture.raw)
                        print(json.dumps(dict(case=case,seed=seed,enabled=enabled,error=type(exc).__name__)),flush=True)
                    report['rows'].append(row)
                    args.output.parent.mkdir(parents=True,exist_ok=True)
                    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,
                        default=lambda value: value.model_dump()),encoding='utf-8')
    finally:
        service.client.close()


if __name__=='__main__':
    main()
