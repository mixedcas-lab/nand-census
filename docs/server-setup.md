# 연구실 서버 작업 안내 — NAND Census 추가 (2026-10-27)

서버에서 이 문서를 위에서부터 따라 하면 됩니다. Claude Code에게 맡길 때는 맨 아래 "Claude Code에게 맡길 때"를 보세요.

---

## 0. 오늘 바뀐 것 (배경)

| 저장소 | 바뀐 내용 | 서버 작업 |
|---|---|---|
| **adc-census** | 공용 수집기 `collector/venues.json`의 `queries`에 IMW·NVSMW(전체), IEDM·TED(NAND/flash 키워드만)를 추가함. ADC Census 사이트에는 안 나옴(`venues`에 없음). 테스트 추가, 통과. | 없음. cron의 `update.sh`가 시작할 때 `git pull` 하므로 자동 반영 |
| **nand-census** (신규) | NAND flash 논문 목록 사이트. 서지 정보·주제 태그·회사 태그만, 수치 없음. 공용 캐시를 읽기만 함. `data/`는 아직 비어 있음 | **deploy key, clone, cron 등록 필요 (아래 2번)** |
| adc/dac/pll/ldo/pmic-census | 상단 메뉴에 NAND 링크 추가 | 없음 |
| 마감일 띠 (adc-census `deadlines.*`) | 9개 Census 공용. 학회 데이터는 `adc-census/deadlines.json` 하나 | 없음. 매월 1일 08:45 클라우드 예약 작업이 갱신 |

전체 흐름(설정 후 매일):

```
06:17  adc-census/scripts/update.sh   IEEE API → ~/adc-census/cache/raw (IMW·IEDM·TED 포함)
06:57  nand-census/scripts/update.sh  캐시 읽기 → data/papers.json → commit·push → GitHub Pages
```

---

## 1. adc-census: 새 venue 수집 확인

새 query가 추가되면 수집기가 빠진 (venue, 연도) 작업을 자동으로 큐에 넣고, 월간 갱신일(15일)을 기다리지 않고 **다음 실행에서 바로** 받습니다. 예상 호출 수는 약 90회(IMW 2009–2026, NVSMW 1997–2008, IEDM·TED 1997–2026)로 하루 한도(190회) 안입니다.

```bash
cd ~/adc-census
git pull --rebase origin main
python3 -m unittest discover -s collector      # 통과 확인 (52 tests)
python3 collector/collect.py --status          # 현재 sweep 상태
```

- **내일 06:17 cron을 기다려도 되고**, 지금 바로 받으려면:
  ```bash
  scripts/update.sh >> logs/update.log 2>&1; tail -30 logs/update.log
  ```
  로그에 `queued ... new sweep tasks`가 나오고 IMW·NVSMW·IEDM·TED 연도별 작업이 진행되면 정상입니다.
- 받은 뒤 `python3 collector/collect.py --status`가 `sweep: done`이면 끝입니다. 한도에 걸려 `in progress`면 다음 날 cron이 이어서 받습니다(종료 코드 3은 정상).
- **ADC 사이트에 영향 없음 확인**: `python3 collector/collect.py --report` 목록에서 IMW·IEDM·TED 출판물은 `DROPPED`로 나와야 합니다(ADC venue가 아니므로 정상).
- 특정 venue가 0건이면 `--report`의 "returned 0 records" 목록을 보고 `collector/venues.json`의 해당 query(`publication_title` 또는 `querytext`)를 고칩니다.

---

## 2. nand-census: 서버 1회 설정

### 2-1. deploy key 만들기 (서버)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/nand_census -N "" -C "nand-census@lab-server"
cat ~/.ssh/nand_census.pub
```

### 2-2. GitHub에 등록 (웹)

https://github.com/mixedcas-lab/nand-census → **Settings → Deploy keys → Add deploy key**
- Title: `lab-server`
- Key: 위에서 출력된 한 줄 전체
- **Allow write access 체크** (서버가 data를 push해야 함)

### 2-3. clone과 cron 등록 (서버)

```bash
cat >> ~/.ssh/config <<'CFG'
Host github-nand-census
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/nand_census
  IdentitiesOnly yes
CFG

git clone github-nand-census:mixedcas-lab/nand-census.git ~/nand-census
cd ~/nand-census
git config user.name "MCAS Lab bot"
git config user.email "연구실-메일-주소"      # 다른 Census 저장소와 같은 주소
mkdir -p logs
python3 -m unittest discover -s collector      # 16 tests 통과 확인

( crontab -l; echo "57 6 * * * PYTHON=$(command -v python3) $HOME/nand-census/scripts/update.sh >> $HOME/nand-census/logs/update.log 2>&1" ) | crontab -
crontab -l | grep -E "adc-census|nand-census"   # 06:17 adc, 06:57 nand 두 줄 확인
```

- `git clone`에서 `Permission denied (publickey)`가 나오면 2-2에서 키를 다른 저장소에 넣었거나 write 체크를 빠뜨린 경우입니다. `ssh -T github-nand-census`로 확인합니다.

---

## 3. 첫 빌드와 확인

```bash
cd ~/nand-census
python3 collector/build.py --report     # venue·연도별 건수, 무작위 표본, 놓친 후보
scripts/update.sh                       # 재생성 → commit → push
tail -20 logs/update.log
```

- 1번의 IMW·IEDM·TED 수집이 끝나기 전이면 ISSCC·JSSC·VLSI 등 회로 venue의 NAND 논문만 먼저 나옵니다. 수집이 끝난 다음 날 06:57 실행에서 자동으로 채워집니다.
- `--report`의 "not NAND by title although it mentions flash…" 목록에 NAND 논문이 섞여 있으면 `collector/classify.py`의 `NAND_PAT`를 보완합니다(테스트 추가 후 커밋).
- 무작위 표본에 NAND가 아닌 논문이 있으면 `NOT_NAND`/`NOR_ONLY`를 보완하거나, 개별 건은 `data/overrides.csv`에 `exclude`로 넣습니다.

---

## 4. GitHub Pages 켜기 (웹, 1회)

https://github.com/mixedcas-lab/nand-census → **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: **main / (root)**

몇 분 뒤 https://mixedcas-lab.github.io/nand-census/ 가 열립니다. 데이터가 없을 때는 "The paper index is being built." 안내가 나옵니다.

---

## 5. 확인 체크리스트

- [ ] `~/adc-census`: `git pull` 후 테스트 통과, `--status`에서 IMW·NVSMW·IEDM·TED 작업이 큐에 있거나 완료
- [ ] deploy key 등록(쓰기 권한), `~/nand-census` clone 성공
- [ ] `crontab -l`에 06:17 adc-census, 06:57 nand-census 두 줄
- [ ] `scripts/update.sh` 실행 후 `logs/update.log`에 `pushed (N NAND papers)`
- [ ] GitHub Pages 켜짐, 사이트에 목록·필터·상단 마감일 띠(CICC, VLSI, IMW, IEDM…) 표시
- [ ] 다른 Census 상단 메뉴의 NAND 링크 동작

---

## 6. 문제 해결

| 증상 | 확인 |
|---|---|
| `cache directory not found` | `collector/venues.json`의 `cache`(`~/adc-census/cache/raw`) 경로, 또는 `NAND_CENSUS_CACHE` 환경변수 |
| `no NAND papers found ... keeping the old data` | 캐시가 비었거나 경로가 바뀜. 기존 데이터는 보존됨 |
| IMW·IEDM·TED가 0건 | `cd ~/adc-census && python3 collector/collect.py --status`로 sweep 진행 확인. 끝났는데 0건이면 `--report`의 0-record 목록 확인 |
| `git push failed` | `cd ~/nand-census && git status && git pull --rebase origin main` (웹에서 overrides.csv를 고친 경우 충돌 가능) |
| 사이트가 예전 그대로 | GitHub Pages 반영 1–2분, 브라우저 `Ctrl+F5` |

---

## 7. 운영 메모

- **오분류 고치기**: 사이트의 각 논문 아래 **Report** → GitHub 이슈. 연구실이 GitHub 웹에서 `data/overrides.csv`에 행 추가(`id,action,topics,note`; action은 `exclude`/`core`/빈칸). 재수집 없이 즉시 반영.
- **분류 규칙**: `collector/classify.py` 수정 → `collector/test_build.py`에 사례 추가 → `python3 -m unittest discover -s collector` 통과 → 커밋. 다음 cron에서 전체 재분류.
- **수치 필드는 넣지 않음**(용량·층수·속도 등).
- **마감일 띠**: 서버 작업 없음. `adc-census/deadlines.json`의 `fields`에 `nand`가 있는 학회가 표시되고, 매월 1일 08:45(KST) 클라우드 예약 작업이 공식 CFP를 확인해 갱신·push합니다.

---

## Claude Code에게 맡길 때

서버에서 `~/nand-census`(또는 clone 전이면 `~/adc-census`)를 열고 다음처럼 요청하면 됩니다. deploy key 등록(2-2)과 Pages 설정(4)은 GitHub 웹 작업이라 사람이 해야 합니다.

```
docs/server-setup.md를 읽고 1번(adc-census 새 venue 확인)과 3번(첫 빌드)을 진행해 줘.
2-1의 키 생성과 2-3의 clone·cron 등록도 해 줘. 공개키를 출력하면 내가 GitHub에 등록할게.
sudo나 다른 사용자 crontab은 건드리지 말고, 각 저장소의 CLAUDE.md 규칙을 지켜 줘.
끝나면 5번 체크리스트 결과를 알려 줘.
```
