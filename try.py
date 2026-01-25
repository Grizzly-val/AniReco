from fastapi import FastAPI
import httpx
import uvicorn

app = FastAPI()

item: int = 3
page: int = 1


@app.get("/top")
def top():
    with httpx.Client() as client:
        response = client.get(f"https://api.jikan.moe/v4/seasons/now?page={page}").json()

        print("="*70)
        for i in range(len(response["data"])):
            print(f"SeasonNow: {response["data"][i]["title"]}")
        print("="*70)

        return response["data"][item]["title"]


@app.get("/anime")
def anime():
    with httpx.Client() as client:
        response = client.get(f"https://api.jikan.moe/v4/anime?status=airing&order_by=scored_by&sort=desc&page={page}").json()

        print("="*70)
        for i in range(len(response["data"])):
            print(f"StatusAiring: {response["data"][i]["title"]}")
        print("="*70)

        return response["data"][item]["title"]
    


@app.get("/test")
def test():
    with httpx.Client() as client:
        response = client.get(f"https://api.jikan.moe/v4/anime?q=pro gamer&order_by=popularity&page={page}").json()

        print("="*70)
        for i in range(len(response["data"])):
            print(f"TestReqs: {response["data"][i]["title"]}")
        print("="*70)

        return response["data"][item]["title"]
    

if __name__ == "__main__":
    uvicorn.run(app="try:app", host="localhost", port=8000, reload=True)




"""
Conclusions (Comparisons):

No Params                                   |          Using Params
======================================================================================================
https://api.jikan.moe/v4/top/anime          |   https://api.jikan.moe/v4/anime?order_by=score&sort=desc
https://api.jikan.moe/v4/seasons/now        |   https://api.jikan.moe/v4/anime?status=airing&order_by=scored_by&sort=desc


"""
        