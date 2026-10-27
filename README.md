# NAND Census

NAND flash 논문 목록: https://mixedcas-lab.github.io/nand-census/

ISSCC·VLSI·JSSC·CICC·ESSCIRC/ESSERC·A-SSCC·SSC-L·TCAS-I/II·TVLSI와 메모리 소자 venue인 IMW(구 NVSMW)·IEDM·IEEE TED에서 NAND flash 논문을 골라, 서지 정보와 주제 태그로 정리합니다. 용량·층수·속도 같은 수치는 추출하지 않습니다. 서울시립대학교 MCAS Lab이 관리합니다.

## 구성

```
index.html, app.js, style.css   사이트 (검색·필터·목록·CSV, 그래프 없음)
collector/build.py              캐시 → data/papers.json, data/meta.json
collector/classify.py           NAND 판별, 주제 태그, 회사 태그 (정규식)
collector/venues.json           venue 이름 매칭, 캐시 위치, 시작 연도
collector/test_build.py         오프라인 테스트
data/overrides.csv              사람이 고친 값: 논문 제외, 주제 태그 교체
scripts/update.sh               랩 서버 cron용: 재생성 → 커밋 → push
docs/server-setup.md            랩 서버 설정·첫 빌드 안내 (서버 작업용)
```

## 동작 방식

1. **데이터**: adc-census 수집기가 랩 서버 캐시(`~/adc-census/cache/raw`)에 회로 venue 전체 논문과 IMW·NVSMW 전체, IEDM·TED의 NAND/flash 키워드 검색 결과를 받아 둡니다. 이 저장소는 그 캐시를 읽기만 하므로 IEEE API를 따로 쓰지 않습니다.
2. **판별**: 제목에 NAND, flash memory, V-NAND, charge-trap/floating-gate flash, page buffer, 3D NAND 등이 있으면 core입니다. flash ADC·NAND gate·NOR/embedded flash는 제외합니다. 제목에는 없고 초록에만 NAND가 나오거나, NAND가 제목에 없는 SSD 시스템 논문은 related입니다.
3. **태그**: 주제(Chip, Sensing/page buffer, HV/WL driver, I/O interface, Program/erase scheme, Controller/ECC/SSD, Reliability, Device/cell, Compute/search)는 제목과 초록 첫 두 문장에서, 회사(Samsung, SK hynix, Kioxia/Toshiba, Western Digital, Micron, Intel/Solidigm, YMTC, Macronix)는 저자 소속에서 붙입니다.
4. **공개**: cron이 매일 06:57(adc-census 06:17 갱신 뒤) 재생성하고, 바뀐 것이 있으면 커밋·push합니다.

## 잘못 분류된 논문 고치기

사이트의 각 논문 아래 **Report**를 누르면 GitHub 이슈 작성 화면이 열립니다. 연구실은 이슈를 확인해 GitHub 웹에서 `data/overrides.csv`에 행을 추가합니다. 수집기를 다시 돌릴 필요 없이 사이트에 즉시 반영됩니다.

| 열 | 내용 |
|---|---|
| `id` | IEEE article number (Xplore 주소 끝의 숫자) |
| `action` | `exclude`: 목록에서 제외, `core`: related를 core로 올림, 비우면 태그만 교체 |
| `topics` | 주제 태그를 `;`로 구분해 통째로 교체 (예: `Chip;I/O interface`) |
| `note` | 논문 아래에 표시할 메모 (선택) |

분류 규칙 자체를 고칠 때는 `collector/classify.py`를 고치고 `collector/test_build.py`에 사례를 추가한 뒤 `python3 -m unittest discover -s collector`가 통과하면 커밋합니다. 다음 cron 실행 때 전체가 재분류됩니다.

## 데이터 필드 (`data/papers.json`)

| 필드 | 내용 |
|---|---|
| `id`, `doi`, `url` | IEEE article number, DOI, Xplore 주소 |
| `t`, `v`, `vt` | 제목, venue 약칭, 원래 출판물 이름 |
| `y`, `d` | 출판 연도, 연-월 |
| `au`, `org`, `cn`, `co` | 저자, 소속(최대 5), 국가, 회사 태그 |
| `lv` | `core` 또는 `related` |
| `tp` | 주제 태그 |
| `ct` | `C` 학회, `J` 저널, `EA` early access |
| `first`, `ins` | 사이트에 처음 실린 날, IEEE 등록일 |

## 랩 서버 설정 (1회)

adc-census가 같은 서버에 설정되어 있어야 합니다(`~/adc-census/cache/raw`). adc-census가 IMW·IEDM·TED를 받아 오도록 바뀐 것은 adc-census 저장소에 이미 반영되어 있으며, adc-census cron이 다음 실행 때 하루 안에 받아 옵니다.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/nand_census -N "" -C "nand-census@lab-server"   # 공개키를 저장소 Deploy keys에 쓰기 권한으로 등록
cat >> ~/.ssh/config <<'CFG'
Host github-nand-census
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/nand_census
  IdentitiesOnly yes
CFG
git clone github-nand-census:mixedcas-lab/nand-census.git ~/nand-census
cd ~/nand-census && git config user.name "MCAS Lab bot" && git config user.email "연구실-메일-주소"
mkdir -p logs
( crontab -l; echo "57 6 * * * PYTHON=$(command -v python3) $HOME/nand-census/scripts/update.sh >> $HOME/nand-census/logs/update.log 2>&1" ) | crontab -
```

GitHub Pages: 저장소 **Settings → Pages**에서 Source를 **Deploy from a branch**, Branch를 **main / (root)**로 지정합니다.

## 학회 마감일 띠

페이지 상단의 마감일 띠는 모든 Census 사이트가 함께 쓰며, adc-census 저장소의 `deadlines.json`에서 `fields`에 `nand`가 있는 학회를 보여 줍니다.
