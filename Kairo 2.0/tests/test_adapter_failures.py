import asyncio
from kairo.application import Application
from kairo.contracts import Tool, parameters


def test_external_exception_returns_to_planner_without_provider_body(tmp_path):
    app=Application(tmp_path)
    class ExternalError(Exception): pass
    def fail(_): raise ExternalError('private provider diagnostic body')
    app.tools.add(Tool('external_failure','Failure fixture',parameters(),lambda a:a,fail))
    result=asyncio.run(app.tools.call('test','external_failure',{},set()))
    assert 'ExternalError' in result['error']
    assert 'private provider' not in result['error']
    assert app.journal.activity()[0]['outcome']=='failed'
    app.journal.close()
