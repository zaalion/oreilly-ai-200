using Azure.Identity;
using OpenAI.Responses;
using System.ClientModel.Primitives;

#pragma warning disable OPENAI001

var builder = WebApplication.CreateBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddConsole();

string endpoint = builder.Configuration["Foundry:Endpoint"]
    ?? throw new InvalidOperationException("Foundry:Endpoint is required.");
string deploymentName = builder.Configuration["Foundry:DeploymentName"]
    ?? throw new InvalidOperationException("Foundry:DeploymentName is required.");

BearerTokenPolicy tokenPolicy = new(
    new DefaultAzureCredential(),
    "https://ai.azure.com/.default");

ResponsesClient responsesClient = new(
    authenticationPolicy: tokenPolicy,
    options: new ResponsesClientOptions
    {
        Endpoint = new Uri(endpoint.TrimEnd('/') + "/"),
    });

builder.Services.AddSingleton(responsesClient);

var app = builder.Build();

app.UseDefaultFiles();
app.UseStaticFiles();

app.MapPost("/api/ask", async (
    AskRequest request,
    ResponsesClient client,
    ILogger<Program> logger) =>
{
    string question = request.Question?.Trim() ?? string.Empty;

    if (question.Length == 0)
    {
        return Results.BadRequest(new ErrorResponse("Enter a question."));
    }

    if (question.Length > 4_000)
    {
        return Results.BadRequest(new ErrorResponse(
            "Questions must be 4,000 characters or fewer."));
    }

    try
    {
        CreateResponseOptions options = new()
        {
            Model = deploymentName,
            InputItems =
            {
                ResponseItem.CreateUserMessageItem(question),
            },
        };

        var response = await client.CreateResponseAsync(options);
        string answer = response.Value.GetOutputText();

        return Results.Ok(new AskResponse(answer));
    }
    catch (Exception exception)
    {
        logger.LogError(exception, "The Foundry model request failed.");
        return Results.Problem(
            title: "The model request failed.",
            detail: "Verify the application's Azure identity, model access, and Foundry configuration.",
            statusCode: StatusCodes.Status502BadGateway);
    }
});

app.Run();

internal sealed record AskRequest(string? Question);
internal sealed record AskResponse(string Answer);
internal sealed record ErrorResponse(string Error);

#pragma warning restore OPENAI001
