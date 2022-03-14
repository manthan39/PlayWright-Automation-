const common =`
    --require setup/assertions.js
    --require setup/hooks.js
    --require step-definations/**/*.step.js
`

module.exports={
    default:`${common} features/**/*.feature`,
}