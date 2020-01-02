사이월드 포스트들을 html로 저장해줍니다. https://github.com/leegeunhyeok/cyworld-bot 를 참조해서 만들었습니다.

# 사용법

1. `driver` 폴더에 크롬 드라이버 설치 (참고: https://github.com/leegeunhyeok/cyworld-bot)
2. 라이브러리 설치 (`conda` 혹은 `pip` 이용)

    ```bash
    pip install -r requirements.txt
    ```

3. 아이디와 비밀번호를 os environment에 저장

    ```bash
    export CYWORLD_EMAIL="USERID"; export CYWORLD_PASSWORD="PASSWORD"
    ```

4. 컨텐트 아이디 다운로드 (중간에 멈추더라도 다시 실행하면 이어서 다운받음)

    ```bash
    python get_content_ids.py
    ```

5. 컨텐츠 다운로드 (중간에 멈추더라도 다시 실행하면 이어서 다운받음)
    
    ```bash
    python download_contents.py
    ```

다운받은 각각의 포스트는 `posts` 폴더안에 `posts/yyyy/mm/yyyymmdd_title_contentid.html`로 저장되고 이미지들도 비슷한 이름으로 같은 폴더에 저장됩니다. 저장되는 HTML파일 형식을 바꾸려면 `template.html`을 바꾸면 됩니다. 
