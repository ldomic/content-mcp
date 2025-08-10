from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("content")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')