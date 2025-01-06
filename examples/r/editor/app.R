library(shiny)
library(bslib)

ui <- page_fluid(
  sliderInput("n", "N", 100, min = 0, max = 200),
  verbatimTextOutput("result")
)

server <- function(input, output, session) {
  output$result <- renderPrint({
    cat("n * 2 =", input$n * 2)
  })
}

shinyApp(ui, server)
