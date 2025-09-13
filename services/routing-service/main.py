from fastapi import FastAPI
from pydantic import BaseModel
import os
from deimos_router import Router, Rule

rules = [
  Rule(name="extract.bug",
       when=lambda m: (not m.get("has_images")) and (m.get("tokens",0) < 1200),
       route={"model":"cheap-summarizer","task":"extract_bug"}),
  Rule(name="vision.parse",
       when=lambda m: m.get("has_images") is True,
       route={"model":"multimodal","task":"vision_parse"}),
  Rule(name="code.map",
       when=lambda m: m.get("needs_code_map") is True,
       route={"model":"strong-coder","task":"code_map"}),
]

router = Router(
  rules=rules,
  api_url=os.getenv("DEIMOS_API_URL","https://api.withmartian.com/v1"),
  api_key=os.getenv("DEIMOS_API_KEY")  # or secrets.json in deimos-router
)

class RouteIn(BaseModel):
  task: str
  metadata: dict = {}
  payload: dict

app = FastAPI()

@app.post("/route")
def route(inp: RouteIn):
  decision = router.decide(inp.task, inp.metadata)
  result = router.execute(decision, inp.payload)
  return {"model": decision.route["model"], "task": decision.route["task"],
          "output": result.get("output"), "usage": result.get("usage")}
