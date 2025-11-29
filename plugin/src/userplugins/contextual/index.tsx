import definePlugin from "@utils/types";

export default definePlugin({
    name: "Contextual",
    description: "Natural language GIF search powered by AI semantic understanding",
    authors: [{ name: "Jon", id: 0n }],
    patches: [],
    settings: {
        apiEndpoint: {
            type: "string",
            default: "http://localhost:8000",
            description: "Backend API endpoint"
        }
    }
});
