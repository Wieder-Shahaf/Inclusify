import asyncio
from unittest.mock import AsyncMock
from app.modules.admin.queries import get_analytics_kpis

async def test_mock_analytics():
    print("Setting up mocked asyncpg connection...")
    
    # Create an AsyncMock to represent the asyncpg.Connection
    mock_conn = AsyncMock()
    
    # We mock fetchval to return a hardcoded integer
    # get_analytics_kpis calls fetchval 4 times for its metrics
    mock_conn.fetchval.return_value = 10
    
    print("Running get_analytics_kpis with mock connection...")
    try:
        # If the datetime/ZoneInfo initialization fails, it will raise an exception here
        kpis = await get_analytics_kpis(mock_conn, days=30)
        
        print("\n=== Mocked Analytics KPIs ===")
        for key, value in kpis.items():
            print(f"{key}: {value}")
            
        print("\n[SUCCESS] Mock test passed! No Python datetime or timezone exceptions occurred.")
        
        # Verify that fetchval was called and verify we handled the timezone variable properly
        call_args_list = mock_conn.fetchval.call_args_list
        print(f"\nVerified: fetchval was called {len(call_args_list)} times.")
        
        # We can extract the cutoff argument from one of the calls to show it's correctly generated
        # The queries taking 'cutoff' pass it as the second argument (the first is the query string)
        for i, call in enumerate(call_args_list):
            if len(call.args) > 1:
                cutoff_arg = call.args[1]
                print(f"Call {i} passed cutoff parameter: {cutoff_arg} (tzinfo: {cutoff_arg.tzinfo})")
                break
                
    except Exception as e:
        print(f"\n[ERROR] Mock test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mock_analytics())
