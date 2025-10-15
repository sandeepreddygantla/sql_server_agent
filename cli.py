from src.agent.sql_agent import sql_agent

def main():
    # Create agent
    agent = sql_agent()

    print("=" * 60)
    print("SQL Server Agent Interactive CLI")
    print("=" * 60)
    print("\nType 'exit' to quit\n")

    while True:
        # Get user input
        query = input("You: ")

        if query.lower() in ['exit', 'quit', 'q']:
            print("\nGoodbye!")
            break

        if not query.strip():
            continue

        # Get agent response
        print("\nAgent:")
        agent.print_response(query, markdown=True)
        print()

if __name__ == "__main__":
    main()
