import asyncio
from flask import Flask, render_template_string, request, jsonify
from playwright.async_api import async_playwright

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MAGIC MUSIC | TikTok Video Fetcher</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 20px;
            background-color: #f4f4f9;
            color: #333;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #1DA1F2;
            margin-bottom: 20px;
        }
        form {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            width: 300px;
            text-align: center;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #1DA1F2;
            color: white;
            border: none;
            padding: 10px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
            width: 100%;
        }
        button:hover {
            background-color: #0e90d2;
        }
        #results {
            margin-top: 20px;
            width: 700px;
        }
        #results ul {
            list-style-type: none;
            padding: 0;
        }
        
        a {
            color: #1DA1F2;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>MAGIC MUSIC | TikTok Video Fetcher</h1>
    <form id="fetchForm">
        <label for="username">Enter TikTok Username:</label>
        <input type="text" id="username" name="username" required>
        <button type="submit">Fetch Videos</button>
    </form>
    <div id="results"></div>

    <script>
        $('#fetchForm').on('submit', function(event) {
            event.preventDefault();
            const username = $('#username').val();

            $.post('/fetch', { username: username }, function(data) {
                let results = '<h2>Video Results:</h2><ul>';
                data.forEach(video => {
                    results += `<li>Video URL: <a href="${video.video_url}" target="_blank">${video.video_url}</a> - Views: ${video.views}</li>`;
                });
                results += '</ul>';
                $('#results').html(results);
            }).fail(function() {
                $('#results').html('<p>Error fetching data. Please try again.</p>');
            });
        });
    </script>
</body>
</html>
'''



async def fetch_latest_videos(username):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the TikTok profile page
        profile_url = f"https://www.tiktok.com/@{username}"
        await page.goto(profile_url, timeout=120000)
        await page.wait_for_timeout(10000)  # Wait for the user to solve the captcha

        video_data = []
        video_urls_set = set()
        target_videos = 30

        while len(video_data) < target_videos:
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)

            videos = await page.query_selector_all('div[data-e2e="user-post-item"]')

            if not videos:
                break

            for video in videos:
                if len(video_data) >= target_videos:
                    break

                video_link = await video.query_selector('a[href*="/video/"]')
                video_url = await video_link.get_attribute('href') if video_link else None
                view_count_element = await video.query_selector('strong[data-e2e="video-views"]')
                view_count = await view_count_element.inner_text() if view_count_element else "0"

                views = parse_view_count(view_count)

                if video_url and video_url not in video_urls_set:
                    video_urls_set.add(video_url)
                    video_data.append({"video_url": video_url, "views": views})

            if len(video_data) >= target_videos:
                break

        await browser.close()
        return video_data

def parse_view_count(view_count):
    if 'K' in view_count:
        return int(float(view_count.replace('K', '')) * 1000)
    elif 'M' in view_count:
        return int(float(view_count.replace('M', '')) * 1000000)
    elif 'B' in view_count:
        return int(float(view_count.replace('B', '')) * 1000000000)
    else:
        return int(view_count)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/fetch', methods=['POST'])
def fetch():
    username = request.form['username']
    video_data = asyncio.run(fetch_latest_videos(username))
    return jsonify(video_data)

if __name__ == '__main__':
    app.run(debug=True)
