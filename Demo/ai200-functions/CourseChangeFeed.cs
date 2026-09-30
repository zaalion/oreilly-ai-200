using System.Text.Json;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

namespace Ai200.Functions;

public sealed class CourseChangeFeed
{
    private readonly ILogger<CourseChangeFeed> _logger;

    // Azure Functions supplies the logger through dependency injection.
    public CourseChangeFeed(ILogger<CourseChangeFeed> logger)
    {
        _logger = logger;
    }

    [Function(nameof(CourseChangeFeed))]
    public void Run(
        // TRIGGER: CosmosDBTrigger starts this function when the monitored change feed has new changes.
        // INPUT BINDING: The same attribute binds the changed Cosmos DB documents to changedDocuments.
        // The lease container stores checkpoints so processing can resume from the last handled change.
        [CosmosDBTrigger(
            databaseName: "CourseCatalog",
            containerName: "courses",
            Connection = "CosmosConnection",
            LeaseContainerName = "leases",
            CreateLeaseContainerIfNotExists = true)]
        IReadOnlyList<JsonElement> changedDocuments)
    {
        // This demo has no output binding; it writes information to the local console through ILogger.
        // One invocation can contain multiple changed documents, so process every document in the batch.
        _logger.LogInformation(
            "Course change feed triggered with {DocumentCount} document(s).",
            changedDocuments.Count);

        foreach (JsonElement document in changedDocuments)
        {
            // Read the fields used in the demo without requiring a fixed C# model for the whole document.
            string id = ReadString(document, "id");
            string title = ReadString(document, "title");
            string category = ReadString(document, "category");

            // These messages appear in the local Functions console when a course is inserted or updated.
            _logger.LogInformation(
                "Changed course: Id={Id}, Title={Title}, Category={Category}",
                id,
                title,
                category);
            _logger.LogInformation("Document JSON: {Document}", document.GetRawText());
        }
    }

    // Return a readable placeholder when an optional property is absent or is not a JSON string.
    private static string ReadString(JsonElement document, string propertyName)
    {
        return document.TryGetProperty(propertyName, out JsonElement property)
            && property.ValueKind == JsonValueKind.String
                ? property.GetString() ?? "(null)"
                : "(missing)";
    }
}
